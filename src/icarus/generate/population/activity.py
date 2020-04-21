
class Activity:
    uuid = 0

    def __init__(self, activity_type, start, end, maz, group):
        self.activity_type = activity_type
        self.start = start
        self.end = end
        self.maz = maz
        self.group = group
        self.parcel = None
        self.id = None


    def request_id(self):
        if self.id is None:
            Activity.uuid += 1
            self.id = Activity.uuid

    
    def assign_parcel(self, parcel):
        self.parcel = parcel