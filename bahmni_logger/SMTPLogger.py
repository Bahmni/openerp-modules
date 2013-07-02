import logging
import nonblockingloghandler
import logging.handlers

class OpenerpSMTPLogHabdler(logging.handlers.SMTPHandler):
    def emit(self, record):
        logging.handlers.SMTPHandler.emit(self, record)

smtpHandler = OpenerpSMTPLogHabdler(
    mailhost="gmail-smtp-in.l.google.com",
    fromaddr="jss.bahmni@gmail.com",
    toaddrs=["bahmni-jss-support@googlegroups.com"],
    subject=u"Bahmni OpenERP Error"
)

nonblocking_email_handler = nonblockingloghandler.NonblockingLogHandler(smtpHandler)
nonblocking_email_handler.setLevel(logging.ERROR)

rootLogger = logging.getLogger()
rootLogger.addHandler(nonblocking_email_handler)

allLoggersDict = logging.Logger.manager.loggerDict
for loggerName in allLoggersDict:
    logger = allLoggersDict[loggerName]
    try:
        logger.addHandler(nonblocking_email_handler)
    except AttributeError:
        pass
