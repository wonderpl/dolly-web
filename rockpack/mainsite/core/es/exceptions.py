class InvalidSearchIndexPrefix(Exception):
    pass


class MissingTermsList(Exception):
    pass


class InvalidTermCondition(Exception):
    pass


class DocumentMissingException(Exception):
    pass


class IndexMissing(Exception):
    pass


class ExpectedIndex(Exception):
    pass


class MultipleIndicesFound(Exception):
    pass
