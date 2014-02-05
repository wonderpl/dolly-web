import time
from datetime import datetime, timedelta
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.sqs_processor import SqsProcessor


class CronSqsProcessor(SqsProcessor):

    queue_name = app.config['SQS_CRON_QUEUE']
    sqs_delay_limit = 900

    def process_message(self, message):
        commands = manager.get_cron_commands()
        try:
            command = message['command']
            next_run = datetime.strptime(message['next_run'][:19], '%Y-%m-%dT%H:%M:%S')
            interval = commands[command]
        except Exception:
            app.logger.exception('Failed to parse message: %r', message)
            # leave message on queue
            return False
        else:
            app.logger.info('Got cron command: %s: next run %s (%ss)', command, next_run, interval)

        # Check if it's time to run this command now.  Adding 10s leeway so that messages
        # that appear after delay_seconds and close to next_run don't get postponed.
        delta = (next_run - datetime.utcnow()).total_seconds()
        if delta > 10:
            # Need to wait a bit longer until next_run
            self.write_message(command, next_run, delta)
            return True

        start_time = time.time()
        try:
            manager.handle('cron', command)
        except Exception:
            app.logger.exception('Failed to run command: %s', command)
            # message will re-appear on the queue after visibility timeout
            return False

        processing_time = time.time() - start_time
        if processing_time < self.sqs_visibility_timeout:
            # only write new message if this one was processed in time
            self.write_message(command, datetime.utcnow() + timedelta(seconds=interval), interval)
        else:
            app.logger.warning('Cron command %s took %ds', command, processing_time)

    @classmethod
    def write_message(cls, command, next_run, delay_seconds=None):
        message = dict(command=command, next_run=next_run.isoformat())
        if delay_seconds is not None:
            delay_seconds = min(cls.sqs_delay_limit, delay_seconds)
        super(CronSqsProcessor, cls).write_message(message, delay_seconds)

    @classmethod
    def init_messages(cls, commands):
        for command in manager.get_cron_commands():
            if not commands or command in commands:
                cls.write_message(command, datetime.utcnow())

    @classmethod
    def clean_messages(cls):
        attributes = cls.getqueue().get_attributes('All')
        message_count = sum(int(attributes['ApproximateNumberOfMessages' + a])
                            for a in ('', 'Delayed', 'NotVisible'))

        messages = []
        manager_commands = set(manager.get_cron_commands().keys())
        commands = set()
        while True:
            new_messages = cls.getqueue().get_messages(10, 60)
            if not new_messages:
                break
            for message in new_messages:
                messages.append(message)
                command = message.get_body()['command']
                if command not in manager_commands:
                    app.logger.warning('Deleting unknown command: %s', command)
                    message.delete()
                elif command in commands:
                    app.logger.warning('Deleting duplicate command: %s', command)
                    message.delete()
                else:
                    commands.add(command)

        if not len(messages) == message_count:
            app.logger.warning('Failed to read %d messages', message_count - len(messages))

        diff = manager_commands - commands
        if diff:
            app.logger.warning('Missing commands: %s', ', '.join(diff))


if __name__ == '__main__':
    CronSqsProcessor().run()
