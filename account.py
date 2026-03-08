import AIcore as ai
import DBio as db

DB_DATA = None

# 능력치, 평판 등을 담는 계정 클래스
class Account:
    def __init__(self, username, usertype):
        self.UserName = username
        self.UserType = usertype # HUMAN, AI, ROBOT, ASSET
        self.rawAbility = ""
        self.Abilities = [ ]
        self.Elo = 1500
        self.Cost = 1000
        self.IsAvailable = True

    def SetAbility(self, text):
        self.rawAbility = text
        self.Abilities = [ ]
        for ability in ai.SplitAbilities(text):
            self.Abilities.append({
                "description": ability,
                "vector": ai.SentenceEmbedding(ability)
            })

    def SetElo(self, elo):
        self.Elo = elo

    def SetStatus(self, cost, isAvailable):
        self.Cost = cost
        self.IsAvailable = isAvailable

    def toJSON(self):
        data = {
            "UserName": self.UserName,
            "UserType": self.UserType,
            "rawAbility": self.rawAbility,
            "Abilities": self.Abilities,
            "Elo": self.Elo,
            "Cost": self.Cost,
            "IsAvailable": self.IsAvailable
        }
        return data
    
def AddAccount(UserName, UserType, rawAbility, Elo, Cost, IsAvailable):
    global DB_DATA
    DB_DATA = db.Load()
    
    account = Account(UserName, UserType)
    account.SetAbility(rawAbility)
    account.SetElo(Elo)
    account.SetStatus(Cost, IsAvailable)
    DB_DATA.append(account.toJSON())
    db.Save(DB_DATA)
