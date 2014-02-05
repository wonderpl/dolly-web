from rockpack.mainsite import app
from rockpack.mainsite.core.es.api import es_update_channel_videos
from rockpack.mainsite.sqs_processor import SqsProcessor


class ElasticsearchSqsProcessor(SqsProcessor):

    queue_name = app.config['SQS_ELASTICSEARCH_QUEUE']

    def process_message(self, updates):
        try:
            es_update_channel_videos(updates['extant'], updates['deleted'], async=False)
        except Exception, e:
            app.logger.exception('Failed to update channel videos: %s with %s', updates, str(e))
            # message will re-appear on the queue after visibility timeout
            return False
        else:
            app.logger.debug('Ran es_update_channel_videos: %r', updates)


if __name__ == '__main__':
    ElasticsearchSqsProcessor().run()
