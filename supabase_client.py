from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)
print("[supabase_client.py] 当前 SUPABASE_KEY:", os.getenv('SUPABASE_KEY'))

def get_traders(sort_by='profit'):
    """
    Get traders list with different sorting options
    """
    sort_columns = {
        'profit': 'total_profit',
        'followers': 'followers_count',
        'likes': 'likes_count'
    }
    
    sort_column = sort_columns.get(sort_by, 'total_profit')
    
    try:
        response = supabase.table('leaderboard_traders')\
            .select('*')\
            .order(sort_column, desc=True)\
            .limit(20)\
            .execute()
            
        return response.data
    except Exception as e:
        return []

def update_trader_stats(trader_id, stats):
    """
    Update trader statistics
    """
    try:
        response = supabase.table('leaderboard_traders')\
            .update(stats)\
            .eq('id', trader_id)\
            .execute()
            
        return len(response.data) > 0
    except Exception as e:
        return False 