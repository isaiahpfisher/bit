import datetime

class Formatter:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    
    NORMAL_WEIGHT = '\033[22m'
    BOLD = '\033[1m'
    
    RESET = '\033[0m'
    
    @staticmethod
    def format_timestamp(timestamp):
        date = datetime.datetime.fromtimestamp(timestamp)
        return date.strftime("%a %b %d %H:%M:%S %Y")

