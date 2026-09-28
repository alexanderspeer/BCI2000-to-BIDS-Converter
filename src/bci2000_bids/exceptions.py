class BCI2000BIDSError(Exception):
    """Base class for expected application errors."""


class BCI2000ReadError(BCI2000BIDSError):
    pass


class ProfileValidationError(BCI2000BIDSError):
    pass


class BIDSConversionError(BCI2000BIDSError):
    pass


class OutputExistsError(BIDSConversionError):
    pass


class BIDSValidationError(BIDSConversionError):
    pass
