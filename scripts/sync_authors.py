import json
import re
import os.path
import itertools
from operator import itemgetter, attrgetter
from datetime import timedelta, datetime
from urllib.parse import urlparse, parse_qs

from sqlalchemy.orm import load_only

from wecom.apps.worktool.models.author_delivery import AuthorDelivery


class SyncAuthorRules:
    pass


if __name__ == "__main__":
    from runserver import app

    with app.app_context():
        pass
