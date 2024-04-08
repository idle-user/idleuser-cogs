from .api import WEB_URL


class User:
    def __init__(self, data):
        self.id = data["id"]
        self.username = data["username"]
        self.last_login = data["last_login"]
        self.date_created = data["date_created"]
        self.url = WEB_URL + "projects/matches/user?user_id={}".format(self.id)
        self.is_registered = True if self.id else False
        self.discord = None

    @classmethod
    def unregistered_user(cls):
        return cls(
            {
                "id": 0,
                "username": 0,
                "last_login": 0,
                "date_created": 0,
            }
        )
