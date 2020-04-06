
import logging as log

class Validation:
    def __init__(self, database):
        self.database = database

    
    def validate(self):
        log.info('Validating home APN assignment consistency.')
        self.database.cursor.execute('''
            SELECT
                agents.household_id AS household_id,
                COUNT(DISTINCT apn) AS freq
            FROM activities
            INNER JOIN agents
            USING(agent_id)
            WHERE type = 'home'
            GROUP BY household_id; ''')
        result = self.database.cursor.fetchall()
        valid = all(household[1] == 1 for household in result)
        assert valid, 'Multiple apns used per household for home.'

        log.info('All validationtests passed.')