import requests
import pandas as pd
from datetime import date

# Notification center params 
NTFY_SERVER_URL = "https://ntfy.sh"
NTFY_TOPIC = "testtoad2"
ALERT_HISTORY_FILEPATH = 'db/alert_history.csv'


# Functions 
def record_notification(ticker, date):
    """ Cache messg payload so it can be checked before resend"""
    print('Notification Recorded')
    df = pd.read_csv(ALERT_HISTORY_FILEPATH)
    
    # create new row and add to df 
    new_row = pd.DataFrame({'ticker': [ticker], 'date': [date]})
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Overwrite the CSV file
    df.to_csv(ALERT_HISTORY_FILEPATH, index=False)
     
def check_notification_sent(ticker, date):
    """Check cache if notification has been sent already or not, this should be a ticker and date combination. Only one notification per day.
    ticker = ticker.upper()
    date = '2025-01-31' 
    return True if has been sent, False if not 
    """
    df = pd.read_csv(ALERT_HISTORY_FILEPATH)

    # Returns true if ticker and date combo found 
    notification_found = ((df['ticker'] == ticker) & (df['date'] == date)).any()
    return notification_found 


def send_notification(title='no msg', body='no text body', ticker='!NA'):
    """ Check if notification has been sent today, then send notification and record as sent if so"""
    # Get current date
    current_date = date.today()
    formatted_date = current_date.strftime('%Y-%m-%d')

    # Check if notification sent, if check returns False, that means no notificaiton found 
    if not check_notification_sent(ticker, formatted_date):
        response = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body,
            headers={
                "Priority": "3",
                "Title": title  # <--- Add your title here!
            }
        )
        if '200' in str(response):
            record_notification(ticker.upper(), formatted_date)
        else:
            print(f'failed to send notification. Bad API response: {str(response)}')
            None
    else: 
        print('Notification already sent')
        return None 
    

send_notification(title='MORE TREATS PLZ', body='FROM DEFINITILY NOT SPOON',ticker='TEST1')