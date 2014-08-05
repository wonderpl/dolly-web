from wonder.common.sqs import BackgroundSqsProcessor
from rockpack.mainsite.cron_processor import create_app


if __name__ == '__main__':
    BackgroundSqsProcessor(create_app).run()
