from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from supabase import create_client
import yfinance as yf
from datetime import datetime
import pytz
import hashlib
import json
import os
import uuid
import random
import sqlite3
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask_cors import CORS
# import mysql.connector
# from mysql.connector import Error
from werkzeug.utils import secure_filename
import supabase_client  # 用 supabase_client.get_traders 代替
from supabase import Client as SupabaseClient

# Flask应用配置
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key_here')
CORS(app, supports_credentials=True)

# 加载环境变量
load_dotenv()

# Supabase配置（从环境变量读取）
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)
print("[app.py] 当前 SUPABASE_KEY:", key)

# 股票图片映射
STOCK_IMAGES = {
    'AAPL': 'https://logo.clearbit.com/apple.com',
    'MSFT': 'https://logo.clearbit.com/microsoft.com',
    'GOOGL': 'https://logo.clearbit.com/google.com',
    'AMZN': 'https://logo.clearbit.com/amazon.com',
    'META': 'https://logo.clearbit.com/meta.com',
    'TSLA': 'https://logo.clearbit.com/tesla.com',
    'NVDA': 'https://logo.clearbit.com/nvidia.com',
    'JPM': 'https://logo.clearbit.com/jpmorgan.com',
    'V': 'https://logo.clearbit.com/visa.com',
    'WMT': 'https://logo.clearbit.com/walmart.com'
}

# 数据库配置 - 使用 Supabase 替代 MySQL
# db_config = {
#     'host': 'localhost',
#     'user': 'root',
#     'password': 'root',
#     'database': 'trading_platform'
# }

# 数据库连接函数 - 使用 Supabase
def get_db_connection():
    try:
        return supabase
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        return None

def format_datetime(dt_str):
    """将UTC时间字符串转换为美国东部时间并格式化为 DD-MMM-YY 格式"""
    try:
        # 解析UTC时间字符串
        dt = datetime.strptime(dt_str.split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
        # 设置为UTC时区
        dt = pytz.UTC.localize(dt)
        # 转换为美国东部时间
        eastern = pytz.timezone('America/New_York')
        dt = dt.astimezone(eastern)
        # 格式化为 DD-MMM-YY 格式 (Windows 兼容格式)
        day = str(dt.day)  # 不使用 %-d
        return f"{day}-{dt.strftime('%b-%y')}"
    except Exception as e:
        try:
            # 尝试其他格式
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            dt = pytz.UTC.localize(dt)
            eastern = pytz.timezone('America/New_York')
            dt = dt.astimezone(eastern)
            day = str(dt.day)  # 不使用 %-d
            return f"{day}-{dt.strftime('%b-%y')}"
        except:
            return dt_str

def format_date_for_db(dt):
    """将日期格式化为数据库存储格式（UTC）"""
    if isinstance(dt, str):
        try:
            # 尝试解析 DD-MMM-YY 格式
            dt = datetime.strptime(dt, '%d-%b-%y')
        except:
            return dt
    # 确保时区是UTC
    if dt.tzinfo is None:
        eastern = pytz.timezone('America/New_York')
        dt = eastern.localize(dt)
    return dt.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S.%f+00:00')

def get_real_time_price(symbol, asset_type=None):
    symbol = str(symbol).upper().split(":")[0]
    api_key = "YIQDtez6a6OhyWsg2xtbRbOUp3Akhlp4"
    # 加密货币部分略...
    # 股票查法兜底：asset_type为stock或未传但symbol像股票代码
    if (asset_type and ("stock" in asset_type.lower())) or (not asset_type and symbol.isalpha() and 2 <= len(symbol) <= 5):
        url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={api_key}"
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            price = None
            if data.get("results") and "p" in data["results"]:
                price = data["results"]["p"]
            elif data.get("last") and "price" in data["last"]:
                price = data["last"]["price"]
            if price is not None:
                return float(price)
        except Exception as e:
            return None
    # 默认返回None
    return None

def get_historical_data(symbol):
    """获取历史数据"""
    try:
        stock = yf.Ticker(symbol)
        history = stock.history(period="1mo")  # 获取一个月的历史数据
        if not history.empty:
            # 将数据转换为列表格式
            data = []
            for date, row in history.iterrows():
                data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
            return data
        return None
    except Exception as e:
        return None

def get_device_fingerprint():
    """生成设备指纹"""
    user_agent = request.headers.get('User-Agent', '')
    ip = request.remote_addr
    # 可以添加更多设备特征
    fingerprint_data = f"{ip}:{user_agent}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()

def get_next_whatsapp_agent(device_fingerprint):
    """获取下一个可用的WhatsApp客服"""
    try:
        # 测试数据库连接
        try:
            test_query = supabase.table('whatsapp_agents').select('count').execute()
        except Exception as db_error:
            return None
        
        # 检查是否已有分配记录
        try:
            existing_record = supabase.table('contact_records').select('*').eq('device_fingerprint', device_fingerprint).execute()
        except Exception as e:
            return None
        
        if existing_record.data:
            # 如果已有分配，返回之前分配的客服
            agent_id = existing_record.data[0]['agent_id']
            try:
                agent = supabase.table('whatsapp_agents').select('*').eq('id', agent_id).execute()
                return agent.data[0] if agent.data else None
            except Exception as e:
                return None
        
        # 获取所有客服
        try:
            agents = supabase.table('whatsapp_agents').select('*').eq('is_active', True).execute()
            if not agents.data:
                return None
        except Exception as e:
            return None
            
        # 获取所有分配记录，只取agent_id
        try:
            assignments = supabase.table('contact_records').select('agent_id').execute()
            assignment_counts = {}
            for record in assignments.data:
                agent_id = record['agent_id']
                assignment_counts[agent_id] = assignment_counts.get(agent_id, 0) + 1
        except Exception as e:
            assignment_counts = {}
            
        # 选择分配数量最少的客服
        min_assignments = float('inf')
        selected_agent = None
        
        for agent in agents.data:
            count = assignment_counts.get(agent['id'], 0)
            if count < min_assignments:
                min_assignments = count
                selected_agent = agent
        
        if selected_agent:
            # 记录新的分配
            try:
                insert_data = {
                    'device_fingerprint': device_fingerprint,
                    'agent_id': selected_agent['id'],
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': datetime.now(pytz.UTC).isoformat()
                }
                insert_result = supabase.table('contact_records').insert(insert_data).execute()
            except Exception as e:
                # 即使插入失败也返回选中的客服
                pass
        
        return selected_agent
        
    except Exception as e:
        return None

@app.route('/api/get-whatsapp-link', methods=['GET', 'POST'])
def get_whatsapp_link():
    """获取WhatsApp链接API"""
    try:
        device_fingerprint = get_device_fingerprint()
        
        # 获取点击时间
        click_time = None
        if request.method == 'POST':
            data = request.get_json()
            click_time = data.get('click_time')
        
        agent = get_next_whatsapp_agent(device_fingerprint)
        
        if agent:
            # 更新点击时间
            if click_time:
                try:
                    update_data = {
                        'click_time': click_time
                    }
                    update_result = supabase.table('contact_records').update(update_data).eq('device_fingerprint', device_fingerprint).execute()
                except Exception as e:
                    pass
            
            app_link = f"whatsapp://send?phone={agent['phone_number']}"
            return {
                'success': True,
                'app_link': app_link
            }
        else:
            return {
                'success': False,
                'message': "No available support agent, please try again later"
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': "System error, please try again later"
        }

@app.route('/')
def index():
    try:
        # 获取交易数据
        response = supabase.table('trades1').select("*").execute()
        trades = response.data

        if not trades:
            trades = []
        
        for trade in trades:
            # 格式化日期前先保存原始日期用于排序
            if trade.get('exit_date'):
                # 将日期字符串转换为datetime对象用于排序
                try:
                    # 尝试解析数据库中的日期格式
                    exit_date = datetime.strptime(trade['exit_date'].split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
                    trade['original_exit_date'] = exit_date
                except Exception as e:
                    # 如果解析失败，尝试其他格式
                    try:
                        exit_date = datetime.fromisoformat(trade['exit_date'].replace('Z', '+00:00'))
                        trade['original_exit_date'] = exit_date
                    except Exception as e2:
                        trade['original_exit_date'] = datetime.min
                trade['exit_date'] = format_datetime(trade['exit_date'])

            if trade.get('entry_date'):
                try:
                    entry_date = datetime.strptime(trade['entry_date'].split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
                    trade['original_entry_date'] = entry_date
                except Exception as e:
                    try:
                        entry_date = datetime.fromisoformat(trade['entry_date'].replace('Z', '+00:00'))
                        trade['original_entry_date'] = entry_date
                    except:
                        trade['original_entry_date'] = datetime.min
                trade['entry_date'] = format_datetime(trade['entry_date'])
            
            # 优先使用数据库中的 image_url，否则用 STOCK_IMAGES
            trade['image_url'] = trade.get('image_url') or STOCK_IMAGES.get(trade['symbol'], '')
            
            # 计算交易金额和盈亏
            trade['entry_amount'] = trade['entry_price'] * trade['size']
            
            # 如果没有current_price，获取实时价格
            if 'current_price' not in trade or not trade['current_price']:
                current_price = get_real_time_price(trade['symbol'])
                if current_price:
                    trade['current_price'] = current_price
                    # 更新数据库中的价格
                    try:
                        update_response = supabase.table('trades1').update({
                            'current_price': current_price,
                            'updated_at': datetime.now(pytz.UTC).isoformat()
                        }).eq('id', trade['id']).execute()
                    except Exception as e:
                        pass
            
            # 计算当前市值和盈亏
            trade['current_amount'] = trade['current_price'] * trade['size'] if trade.get('current_price') else trade['entry_amount']
            
            # 计算盈亏
            if trade.get('exit_price'):
                trade['profit_amount'] = (trade['exit_price'] - trade['entry_price']) * trade['size']
            else:
                trade['profit_amount'] = (trade['current_price'] - trade['entry_price']) * trade['size'] if trade.get('current_price') else 0
            
            # 计算盈亏比例
            trade['profit_ratio'] = (trade['profit_amount'] / trade['entry_amount']) * 100 if trade['entry_amount'] else 0
            
            # 设置状态
            if trade.get('exit_price') is None and trade.get('exit_date') is None:
                trade['status'] = "Active"
            else:
                trade['status'] = "Closed"
        
        # 分离持仓和平仓的交易
        holding_trades = [t for t in trades if t['status'] == "Active"]
        closed_trades = [t for t in trades if t['status'] == "Closed"]

        holding_trades.sort(key=lambda x: x['original_entry_date'], reverse=True)
        
        closed_trades.sort(key=lambda x: x['original_exit_date'], reverse=True)
        
        # 合并排序后的交易列表
        sorted_trades = holding_trades + closed_trades
        
        # 计算总览数据
        total_trades = len(sorted_trades)
        
        # 获取当前持仓
        positions = holding_trades
        
        # 获取当前美国东部时间的月份
        eastern = pytz.timezone('America/New_York')
        current_time = datetime.now(eastern)
        current_month = f"{str(current_time.day)}-{current_time.strftime('%b-%y')}"
        
        # 计算当月平仓盈亏
        monthly_closed_trades = [t for t in closed_trades 
                               if t.get('exit_date') 
                               and t['exit_date'].split('-')[1] == current_month.split('-')[1]]
        
        monthly_profit = sum(t.get('profit_amount', 0) for t in monthly_closed_trades)

        # 获取所有交易员档案信息
        profile_response = supabase.table('trader_profiles').select("*").execute()
        trader_profiles = profile_response.data if profile_response.data else []
        
        # 调试信息：打印数据库中的数据
        print("=" * 50)
        print("🔍 调试信息：trader_profiles 数据")
        print("=" * 50)
        if trader_profiles:
            for i, profile in enumerate(trader_profiles):
                print(f"📋 交易员 {i+1}:")
                print(f"   - ID: {profile.get('id')}")
                print(f"   - 姓名: {profile.get('trader_name')}")
                print(f"   - 头像URL: {profile.get('profile_image_url')}")
                print("   ---")
        else:
            print("❌ 数据库中没有找到 trader_profiles 数据")
        print("=" * 50)
        
        # 如果没有数据，创建默认数据
        if not trader_profiles:
            trader_profiles = [
                {
                    'id': 1,
                    'trader_name': 'Professional Trader',
                    'professional_title': 'Financial Trading Expert | Technical Analysis Master',
                    'profile_image_url': None,
                    'years_of_experience': 8,
                    'total_trades': 1250,
                    'win_rate': 78.5,
                    'members_count': 1250,
                    'likes_count': 890
                }
            ]
        
        # 获取最新的交易策略
        strategy_response = supabase.table('trading_strategies').select("*").order('updated_at', desc=True).limit(1).execute()
        strategy_info = strategy_response.data[0] if strategy_response.data else {
            'market_analysis': 'Today\'s market shows an upward trend with strong performance in the tech sector. Focus on AI-related stocks...',
            'trading_focus': ['Tech Sector: AI, Chips, Cloud Computing', 'New Energy: Solar, Energy Storage, Hydrogen', 'Healthcare: Innovative Drugs, Medical Devices'],
            'risk_warning': 'High market volatility, please control position size and set stop loss...',
            'updated_at': datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S.%f+00:00')
        }
        
        # 计算总利润
        total_profit = sum(t.get('profit_amount', 0) for t in sorted_trades)

        # 为每个交易员添加交易数据
        for profile in trader_profiles:
            profile['positions'] = positions
            profile['monthly_profit'] = round(monthly_profit, 2)
            profile['active_trades'] = len(positions)
            profile['total_profit'] = round(total_profit, 2)
            profile['strategy_info'] = strategy_info

        
        return render_template('index.html', 
                            trades=sorted_trades,
                            trader_profiles=trader_profiles)
    except Exception as e:
        print("=" * 50)
        print("❌ 主页加载异常:")
        print(f"   错误信息: {str(e)}")
        print("=" * 50)
        return render_template('index.html', 
                            trades=[],
                            trader_profiles=[])

@app.route('/api/trader-profile', methods=['GET'])
def trader_profile():
    try:
        # 获取个人资料
        response = supabase.table('trader_profiles').select('*').limit(1).execute()
        # 获取trades表中的记录数
        trades_response = supabase.table('trades1').select('id').execute()
        trades_count = len(trades_response.data) if trades_response.data else 0
        if response.data:
            profile = response.data[0]
            # 更新总交易次数 = trader_profiles表中的total_trades + trades表中的记录数
            profile['total_trades'] = profile.get('total_trades', 0) + trades_count
            # 头像直接用trader_profiles表中的profile_image_url字段
            # 不再覆盖profile['profile_image_url']
            return jsonify({
                'success': True,
                'data': profile
            })
        else:
            # 如果没有数据，返回默认值
            return jsonify({
                'success': True,
                'data': {
                    'trader_name': 'Professional Trader',
                    'professional_title': 'Stock Trading Expert | Technical Analysis Master',
                    'years_of_experience': 5,
                    'total_trades': trades_count,
                    'win_rate': 85.0,
                    'profile_image_url': None
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/leaderboard')
def leaderboard():
    # Get sort parameter from query string, default to 'profit'
    sort_by = request.args.get('sort', 'profit')
    # Get traders from Supabase
    traders = supabase_client.get_traders(sort_by)
    # If no traders found, return empty list
    if not traders:
        traders = []
    # 补充默认头像
    for trader in traders:
        if not trader.get('profile_image_url'):
            trader['profile_image_url'] = DEFAULT_AVATAR_URL
    return render_template('leaderboard.html', traders=traders)

@app.route('/api/upload-avatar', methods=['POST'])
def upload_avatar():
    try:
        if 'username' not in session:
            return jsonify({'success': False, 'message': 'Not logged in'}), 401
        file = request.files.get('avatar')
        if not file:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[-1].lower()
        allowed_ext = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
        if file_ext not in allowed_ext:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        file_bytes = file.read()
        # 上传到 Supabase Storage
        import uuid
        file_path = f"avatars/avatars/{session['username']}_{uuid.uuid4().hex}.{file_ext}"
        result = supabase.storage.from_('images').upload(file_path, file_bytes, file_options={"content-type": file.mimetype})
        if hasattr(result, 'error') and result.error:
            return jsonify({'success': False, 'message': f'Upload failed: {result.error}'}), 500
        public_url = supabase.storage.from_('images').get_public_url(file_path)
        # 更新数据库
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Not logged in'}), 401
        supabase.table('users').update({'avatar_url': public_url}).eq('id', user_id).execute()
        return jsonify({'success': True, 'url': public_url})
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': 'Upload failed, please try again later'}), 500

@app.route('/api/get-avatar', methods=['GET'])
def get_avatar():
    try:
        # 从数据库获取交易员档案的头像
        response = supabase.table('trader_profiles').select('profile_image_url').limit(1).execute()
        if response.data and response.data[0].get('profile_image_url'):
            return jsonify({'success': True, 'url': response.data[0]['profile_image_url']})
        else:
            # 如果没有头像，返回None而不是默认头像
            return jsonify({'success': True, 'url': None})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to get avatar'}), 500

@app.route('/api/proxy-avatar', methods=['GET'])
def proxy_avatar():
    """代理头像请求，解决CORS问题"""
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({'success': False, 'message': 'No URL provided'}), 400
        
        # 使用requests获取图片
        import requests
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # 返回图片数据
        from flask import Response
        return Response(
            response.content,
            mimetype=response.headers.get('content-type', 'image/jpeg'),
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to proxy image: {str(e)}'}), 500

@app.route('/api/price')
def api_price():
    symbol = request.args.get('symbol')
    trade_id = request.args.get('trade_id')
    asset_type = None

    # 优先用trade_id查表获取asset_type和symbol
    if trade_id:
        # 先查vip_trades表
        trade = supabase.table('vip_trades').select('asset_type,symbol').eq('id', trade_id).execute()
        if trade.data:
            asset_type = trade.data[0].get('asset_type')
            symbol = trade.data[0].get('symbol')
        else:
            # 可选：查trades1等其他表
            trade = supabase.table('trades1').select('asset_type,symbol').eq('id', trade_id).execute()
            if trade.data:
                asset_type = trade.data[0].get('asset_type')
                symbol = trade.data[0].get('symbol')
    else:
        # 没有trade_id时，symbol必须有，asset_type可选
        asset_type = request.args.get('asset_type')

    if not symbol:
        return jsonify({'success': False, 'message': 'No symbol provided'}), 400

    price = get_real_time_price(symbol, asset_type)
    if price is not None:
        return jsonify({'success': True, 'price': float(price)})
    else:
        return jsonify({'success': False, 'message': 'Failed to get price'}), 500

@app.route('/api/history')
def api_history():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({'success': False, 'message': 'No symbol provided'}), 400

    history = get_historical_data(symbol)
    if history is not None:
        return jsonify({'success': True, 'data': history})
    else:
        return jsonify({'success': False, 'message': 'Failed to get historical data'}), 500

def membership_level_class(level):
    """Map membership level to CSS class"""
    level_map = {
        'VIP': 'regular-member',
        'Regular Member': 'regular-member',
        'Gold Member': 'gold-member',
        'Diamond Member': 'diamond-member',
        'Supreme Black Card': 'black-card-member',
        'gold-member': 'gold-member',
        'diamond-member': 'diamond-member',
        'black-card-member': 'black-card-member',
        'regular-member': 'regular-member'
    }
    return level_map.get(level, 'regular-member')

@app.route('/vip')
def vip():
    if 'username' in session:
        response = supabase.table('users').select('*').eq('username', session['username']).execute()
        if response.data:
            user = response.data[0]
            trader_info = {
                'trader_name': user['username'],
                'membership_level': user.get('membership_level', 'VIP Member'),
                'trading_volume': user.get('trading_volume', 0),
                'profile_image_url': None
            }
            user_id = user['id']
            initial_asset = float(user.get('initial_asset', 0) or 0)
            # 获取该用户的交易记录
            trades_resp = supabase.table('trades').select('*').eq('user_id', user_id).execute()
            trades = trades_resp.data if trades_resp.data else []
        else:
            trader_info = {
                'trader_name': session['username'],
                'membership_level': 'VIP Member',
                'trading_volume': 0,
                'profile_image_url': None
            }
            trades = []
            initial_asset = 0
    else:
        trader_info = {
            'membership_level': 'VIP Member',
            'trading_volume': 0,
            'profile_image_url': None
        }
        trades = []
        initial_asset = 0
    # 计算dynamic_total_asset
    total_market_value = 0
    holding_cost = 0
    closed_profit_sum = 0
    for trade in trades:
        entry_price = float(trade.get('entry_price') or 0)
        exit_price = float(trade.get('exit_price') or 0)
        size = float(trade.get('size') or 0)
        current_price = float(trade.get('current_price') or 0)
        if not trade.get('exit_price'):
            total_market_value += current_price * size
            holding_cost += entry_price * size
        else:
            profit = (exit_price - entry_price) * size
            closed_profit_sum += profit
    available_funds = initial_asset + closed_profit_sum - holding_cost
    dynamic_total_asset = total_market_value + available_funds
    return render_template(
        'vip.html',
        trader_info=trader_info,
        trades=trades,
        dynamic_total_asset=dynamic_total_asset,
    )

@app.route('/vip-dashboard')
def vip_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('vip'))
    user_resp = supabase.table('users').select('*').eq('id', user_id).execute()
    user = user_resp.data[0] if user_resp.data else {}
    user = fill_default_avatar(user)
    avatar_url = user.get('avatar_url')
    level_cn = user.get('membership_level', '普通会员')
    level_en = get_level_en(level_cn)
    initial_asset = float(user.get('initial_asset', 0) or 0)

    # 只统计当前用户自己的收益
    trades_resp = supabase.table('trades').select('*').eq('user_id', user['id']).execute()
    trades = trades_resp.data if trades_resp.data else []

    # --- 新增：实时获取未平仓持仓的最新价格 ---
    for trade in trades:
        if not trade.get('exit_price'):
            latest_price = get_real_time_price(trade.get('symbol'))
            if latest_price:
                trade['current_price'] = latest_price
    # --- 其它统计逻辑保持不变 ---
    total_profit = 0
    monthly_profit = 0
    holding_profit = 0
    closed_profit = 0
    now = datetime.now()
    total_market_value = 0
    holding_cost = 0
    closed_profit_sum = 0
    for trade in trades:
        entry_price = float(trade.get('entry_price') or 0)
        exit_price = float(trade.get('exit_price') or 0)
        size = float(trade.get('size') or 0)
        profit = 0
        if not trade.get('exit_price'):
            symbol = trade.get('symbol')
            if not symbol:
                print(f"[HoldingProfit] WARNING: 持仓有空symbol，entry_price={entry_price}, size={size}")
                continue
            # 用本地API查价，和前端一致
            try:
                resp = requests.get(f"http://127.0.0.1:5000/api/price?symbol={symbol}", timeout=3)
                data = resp.json()
                latest_price = data.get('price') if data.get('success') else None
            except Exception as e:
                print(f"[HoldingProfit] ERROR: 请求本地/api/price失败: {e}")
                latest_price = None
            print(f"[HoldingProfit] symbol={symbol}, entry_price={entry_price}, latest_price={latest_price}, size={size}")
            if latest_price is not None:
                profit = (latest_price - entry_price) * size
                holding_profit += profit
            else:
                print(f"[HoldingProfit] WARNING: /api/price?symbol={symbol} 返回None，无法计算持仓利润")
            total_market_value += (latest_price or 0) * size
            holding_cost += entry_price * size
        else:
            profit = (exit_price - entry_price) * size
            closed_profit_sum += profit
        if trade.get('exit_price') is not None:
            profit = (exit_price - entry_price) * size
            total_profit += profit
            if trade.get('exit_date') and str(trade['exit_date']).startswith(now.strftime('%Y-%m')):
                monthly_profit += profit
            closed_profit = total_profit
    available_funds = initial_asset + closed_profit_sum - holding_cost
    dynamic_total_asset = total_market_value + available_funds

    # 查询排行榜
    users_resp = supabase.table('users').select('username,membership_level,avatar_url,monthly_profit,total_profit').order('monthly_profit', desc=True).limit(50).execute()
    top_users = users_resp.data if users_resp.data else []

    trader_info = {
        'trader_name': user.get('username', ''),
        'membership_level': level_en,
        'trading_volume': user.get('trading_volume', 0),
        'avatar_url': avatar_url
    }

    # 查询VIP策略公告（取前2条，按date降序）
    announcements_resp = supabase.table('vip_announcements').select('*').order('date', desc=True).limit(2).execute()
    announcements = announcements_resp.data if announcements_resp.data else []

    # 查询VIP交易记录（取前10条，按entry_time降序）
    vip_trades_resp = supabase.table('vip_trades').select('*').order('entry_time', desc=True).limit(10).execute()
    vip_trades = vip_trades_resp.data if vip_trades_resp.data else []

    # --- trades排序：未平仓排前面，再按entry_date降序 ---
    trades.sort(key=lambda t: (0 if not t.get('exit_price') else 1, t.get('entry_date') or ''), reverse=False)

    return render_template(
        'vip-dashboard.html',
        trader_info=trader_info,
        total_asset=initial_asset,
        dynamic_total_asset=dynamic_total_asset,
        total_market_value=total_market_value,
        available_funds=available_funds,
        total_profit=total_profit,
        monthly_profit=monthly_profit,
        holding_profit=holding_profit,
        trades=trades,
        top_users=top_users,
        membership_level_class=membership_level_class,
        announcements=announcements,
        vip_trades=vip_trades
    )

# --- 用户表自动建表 ---
def init_user_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE,
            status TEXT DEFAULT 'active',
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            last_login_ip TEXT,
            last_login_location TEXT,
            membership_level TEXT DEFAULT '普通会员',
            initial_asset REAL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# --- 会员等级表自动建表 ---
def init_membership_levels_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS membership_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            level INTEGER NOT NULL,
            min_trading_volume DECIMAL(10,2) NOT NULL,
            benefits TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认会员等级
    default_levels = [
        ('普通会员', 1, 0.00, '基础交易工具,标准市场分析,社区访问,标准支持'),
        ('黄金会员', 2, 100000.00, '高级交易工具,实时市场分析,优先支持,VIP社区访问,交易策略分享'),
        ('钻石会员', 3, 500000.00, '所有黄金会员权益,个人交易顾问,定制策略开发,新功能优先体验,专属交易活动'),
        ('至尊黑卡', 4, 1000000.00, '所有钻石会员权益,24/7专属交易顾问,AI量化策略定制,全球金融峰会邀请,专属投资机会,一对一交易指导')
    ]
    
    c.execute('SELECT COUNT(*) FROM membership_levels')
    if c.fetchone()[0] == 0:
        c.executemany('''
            INSERT INTO membership_levels (name, level, min_trading_volume, benefits)
            VALUES (?, ?, ?, ?)
        ''', default_levels)
    
    conn.commit()
    conn.close()

# --- 用户会员等级关联表自动建表 ---
def init_user_membership_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_membership (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            level_id INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (level_id) REFERENCES membership_levels (id)
        )
    ''')
    conn.commit()
    conn.close()

# --- 会员等级分配API ---
@app.route('/api/admin/assign-membership', methods=['POST'])
def assign_membership():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        data = request.get_json()
        if not data.get('user_id'):
            return jsonify({'success': False, 'message': '缺少用户ID'}), 400

        # 根据level_id获取会员等级名称
        membership_levels = {
            '1': '普通会员',
            '2': '黄金会员',
            '3': '钻石会员',
            '4': '至尊黑卡'
        }
        
        level_name = membership_levels.get(str(data.get('level_id')))
        if not level_name:
            return jsonify({'success': False, 'message': '无效的会员等级'}), 400

        # 直接更新users表
        response = supabase.table('users').update({
            'membership_level': level_name
        }).eq('id', data['user_id']).execute()
        
        if not response.data:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
            
        return jsonify({'success': True, 'message': 'Membership level assigned successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Operation failed: {str(e)}'}), 500

# --- 获取用户会员等级信息 ---
@app.route('/api/user/membership', methods=['GET'])
def get_user_membership():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
            
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # 获取用户的会员等级信息
        c.execute('''
            SELECT m.name, m.level, m.benefits
            FROM user_membership um
            JOIN membership_levels m ON um.level_id = m.id
            WHERE um.user_id = ?
        ''', (session['user_id'],))
        
        membership = c.fetchone()
        conn.close()
        
        if membership:
            return jsonify({
                'success': True,
                'membership': {
                    'name': membership[0],
                    'level': membership[1],
                    'benefits': membership[2]
                }
            })
        else:
            return jsonify({
                'success': True,
                'membership': None
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to get membership information'}), 500

# --- 会员等级管理API ---
@app.route('/api/admin/membership-levels', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_membership_levels():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取所有会员等级
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT * FROM membership_levels ORDER BY level')
            levels = []
            for row in c.fetchall():
                levels.append({
                    'id': row[0],
                    'name': row[1],
                    'level': row[2],
                    'min_trading_volume': row[3],
                    'benefits': row[4],
                    'created_at': row[5]
                })
            conn.close()
            return jsonify({'success': True, 'levels': levels})
            
        elif request.method == 'POST':
            # 创建新会员等级
            data = request.get_json()
            required_fields = ['name', 'level', 'min_trading_volume', 'benefits']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('''
                INSERT INTO membership_levels (name, level, min_trading_volume, benefits)
                VALUES (?, ?, ?, ?)
            ''', (data['name'], data['level'], data['min_trading_volume'], data['benefits']))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Membership level created successfully'})
            
        elif request.method == 'PUT':
            # 更新会员等级
            data = request.get_json()
            required_fields = ['id', 'name', 'level', 'min_trading_volume', 'benefits']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('''
                UPDATE membership_levels
                SET name = ?, level = ?, min_trading_volume = ?, benefits = ?
                WHERE id = ?
            ''', (data['name'], data['level'], data['min_trading_volume'], data['benefits'], data['id']))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Membership level updated successfully'})
            
        elif request.method == 'DELETE':
            # 删除会员等级
            level_id = request.args.get('id')
            if not level_id:
                return jsonify({'success': False, 'message': '缺少会员等级ID'}), 400
                
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('DELETE FROM membership_levels WHERE id = ?', (level_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Membership level deleted successfully'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Operation failed'}), 500

# --- 登录接口（Supabase版） ---
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # 从Supabase获取用户信息
        response = supabase.table('users').select('*').eq('username', username).execute()
        
        if not response.data:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
            
        user = response.data[0]
        
        # TODO: 在实际应用中应该进行密码验证
        # 这里简化处理，直接验证密码是否匹配
        if password != user.get('password_hash'):  # 实际应用中应该使用proper密码验证
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
            
        if user.get('status') != 'active':
            return jsonify({'success': False, 'message': 'The account has been disabled.'}), 403
            
        # 获取IP和地址信息
        ip_address = request.remote_addr
        try:
            response = requests.get(f'https://ipinfo.io/{ip_address}/json')
            location_data = response.json()
            location = f"{location_data.get('city', '')}, {location_data.get('region', '')}, {location_data.get('country', '')}"
        except:
            location = 'Unknown location'
            
        # 更新用户登录信息
        supabase.table('users').update({
            'last_login': datetime.now(pytz.UTC).isoformat(),
            'last_login_ip': ip_address,
            'last_login_location': location
        }).eq('id', user['id']).execute()
        
        # 设置session
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user.get('role', 'user')
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user.get('role', 'user'),
                'membership_level': user.get('membership_level', '普通会员')
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Login failed'}), 500

# --- 登出接口 ---
@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        # 清除session
        session.clear()
        return jsonify({'success': True, 'message': 'Successfully logged out'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Logout failed'}), 500

def update_holding_stocks_prices():
    """更新所有持有中股票的实时价格"""
    try:
        # 获取所有持有中的股票
        response = supabase.table('trades1').select("*").execute()
        trades = response.data
        
        if not trades:
            return
        
        for trade in trades:
            # 检查是否是持有中的股票
            if trade.get('exit_price') is None and trade.get('exit_date') is None:
                symbol = trade['symbol']
                current_price = get_real_time_price(symbol)
                
                if current_price:
                    # 计算新的数据
                    entry_amount = trade['entry_price'] * trade['size']
                    current_amount = current_price * trade['size']
                    profit_amount = current_amount - entry_amount
                    profit_ratio = (profit_amount / entry_amount) * 100 if entry_amount else 0
                    
                    try:
                        # 只更新current_price字段
                        update_data = {
                            'current_price': current_price
                        }
                        
                        update_response = supabase.table('trades1').update(update_data).eq('id', trade['id']).execute()
                        
                        if update_response.data:
                            # 验证更新是否成功
                            verify_response = supabase.table('trades1').select('current_price').eq('id', trade['id']).execute()
                    except Exception as e:
                        import traceback
                        print(f"Error updating database: {str(e)}")
                        print(f"Error details: {type(e).__name__}")
                        print(f"Error stack: {traceback.format_exc()}")
                
                else:
                    pass
            else:
                pass
                
    except Exception as e:
        import traceback
        print(f"Error updating stock prices: {str(e)}")
        print(f"Error stack: {traceback.format_exc()}")

def update_all_trades_prices():
    """同步所有交易表的未平仓记录的实时价格"""
    tables = ['trades1', 'trades', 'vip_trades']
    for table in tables:
        try:
            response = supabase.table(table).select("*").execute()
            trades = response.data
            if not trades:
                continue
            for trade in trades:
                # 只同步未平仓（exit_price为空或None）
                if not trade.get('exit_price'):
                    symbol = trade.get('symbol')
                    if not symbol:
                        continue
                    current_price = get_real_time_price(symbol)
                    if current_price:
                        try:
                            supabase.table(table).update({'current_price': current_price}).eq('id', trade['id']).execute()
                        except Exception as e:
                            print(f"{table} {symbol} update failed: {e}")
                    else:
                        print(f"{table} {symbol} failed to get real-time price")
        except Exception as e:
            print(f"Error synchronizing {table}: {e}")

# 创建调度器
scheduler = BackgroundScheduler()
scheduler.start()

# 添加定时任务，每30秒更新一次价格
scheduler.add_job(
    func=update_holding_stocks_prices,
    trigger=IntervalTrigger(seconds=30),  # 改为30秒
    id='update_stock_prices',
    name='Update holding stocks prices every 30 seconds',
    replace_existing=True
)

# 替换原有定时任务为统一同步
scheduler.add_job(
    func=update_all_trades_prices,
    trigger=IntervalTrigger(seconds=30),
    id='update_all_trades_prices',
    name='Update all trades prices every 30 seconds',
    replace_existing=True
)

print("价格更新定时任务已启动，每30秒更新一次")

@app.route('/api/check-login', methods=['GET'])
def check_login():
    try:
        if 'user_id' in session:
            # 获取用户信息
            response = supabase.table('users').select('*').eq('id', session['user_id']).execute()
            if response.data:
                user = fill_default_avatar(response.data[0])
                level_cn = user.get('membership_level', '普通会员')
                level_en = get_level_en(level_cn)
                return jsonify({
                    'isLoggedIn': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'role': user.get('role', 'user'),
                        'email': user.get('email'),
                        'avatar_url': user.get('avatar_url'),
                        'membership_level': level_en
                    }
                })
        return jsonify({'isLoggedIn': False})
    except Exception as e:
        return jsonify({'isLoggedIn': False}), 500

# --- 管理员接口 ---
@app.route('/api/admin/users', methods=['GET', 'POST'])
def manage_users():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取所有用户
            response = supabase.table('users').select('*').execute()
            # 过滤敏感信息
            users = []
            for user in response.data:
                user = fill_default_avatar(user)
                level_cn = user.get('membership_level', '普通会员')
                level_en = get_level_en(level_cn)
                users.append({
                    'id': user['id'],
                    'username': user['username'],
                    'email': user.get('email'),
                    'role': user.get('role', 'user'),
                    'status': user.get('status', 'active'),
                    'membership_level': level_en,
                    'last_login': user.get('last_login'),
                    'last_login_ip': user.get('last_login_ip'),
                    'last_login_location': user.get('last_login_location'),
                    'created_at': user.get('created_at'),
                    'avatar_url': user.get('avatar_url'),
                    'initial_asset': user.get('initial_asset', 0)
                })
            return jsonify({'success': True, 'users': users})
            
        elif request.method == 'POST':
            # 创建新用户
            data = request.get_json()
            
            # 检查必要字段
            if not data.get('username') or not data.get('password'):
                return jsonify({'success': False, 'message': '用户名和密码是必填项'}), 400
                
            # 检查用户名是否已存在
            check_response = supabase.table('users').select('id').eq('username', data['username']).execute()
            if check_response.data:
                return jsonify({'success': False, 'message': '用户名已存在'}), 400
                
            # 创建新用户
            new_user = {
                'username': data['username'],
                'password_hash': data['password'],  # 在实际应用中应该对密码进行加密
                'email': data.get('email'),
                'role': data.get('role', 'user'),
                'status': 'active',
                'membership_level': data.get('membership_level', '普通会员'),
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'initial_asset': float(data.get('initial_asset', 0) or 0)
            }
            
            response = supabase.table('users').insert(new_user).execute()
            
            return jsonify({
                'success': True,
                'message': 'User created successfully',
                'user_id': response.data[0]['id']
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Operation failed'}), 500

@app.route('/api/admin/users/<user_id>', methods=['PUT', 'DELETE'])
def update_user(user_id):
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'PUT':
            data = request.get_json()
            # 只允许更新特定字段
            allowed_fields = ['status', 'role', 'password_hash', 'initial_asset', 'membership_level']
            update_data = {k: v for k, v in data.items() if k in allowed_fields}
            if not update_data:
                return jsonify({'success': False, 'message': '没有可更新的字段'}), 400
            # initial_asset转float
            if 'initial_asset' in update_data:
                try:
                    update_data['initial_asset'] = float(update_data['initial_asset'])
                except Exception:
                    update_data['initial_asset'] = 0
            # 更新用户信息
            response = supabase.table('users').update(update_data).eq('id', user_id).execute()
            if not response.data:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            return jsonify({
                'success': True,
                'message': 'Update successful'
            })
        elif request.method == 'DELETE':
            # 软删除用户（更新状态为inactive）
            response = supabase.table('users').update({
                'status': 'inactive',
                'deleted_at': datetime.now(pytz.UTC).isoformat()
            }).eq('id', user_id).execute()
            
            if not response.data:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
                
            return jsonify({
                'success': True,
                'message': '用户已禁用'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Operation failed'}), 500

@app.route('/api/admin/users/batch', methods=['POST'])
def batch_update_users():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        action = data.get('action')  # 'activate' 或 'deactivate'
        
        if not user_ids or action not in ['activate', 'deactivate']:
            return jsonify({'success': False, 'message': '参数错误'}), 400
            
        # 批量更新用户状态
        status = 'active' if action == 'activate' else 'inactive'
        response = supabase.table('users').update({
            'status': status
        }).in_('id', user_ids).execute()
        
        return jsonify({
            'success': True,
            'message': f'已{action} {len(response.data)} 个用户'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '批量操作失败'}), 500

@app.route('/api/admin/logs', methods=['GET'])
def get_login_logs():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        # 获取最近100条登录记录
        response = supabase.table('users').select('username, last_login, status').order('last_login', desc=True).limit(100).execute()
        
        return jsonify({
            'success': True,
            'logs': response.data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取日志失败'}), 500

# --- 测试路由 ---
@app.route('/test/login', methods=['GET'])
def test_login():
    test_cases = [
        {
            'name': '正常登录',
            'data': {'username': 'admin', 'password': '123456'},
            'expected': {'success': True, 'message': '登录成功'}
        },
        {
            'name': '缺少用户名',
            'data': {'password': '123456'},
            'expected': {'success': False, 'message': '请输入账号和密码'}
        },
        {
            'name': '缺少密码',
            'data': {'username': 'admin'},
            'expected': {'success': False, 'message': '请输入账号和密码'}
        },
        {
            'name': '错误密码',
            'data': {'username': 'admin', 'password': 'wrong_password'},
            'expected': {'success': False, 'message': '密码错误'}
        },
        {
            'name': '不存在的用户',
            'data': {'username': 'non_existent_user', 'password': '123456'},
            'expected': {'success': False, 'message': '账号不存在'}
        }
    ]
    
    results = []
    for test in test_cases:
        try:
            # 创建测试请求
            with app.test_request_context('/api/login', method='POST', json=test['data']):
                # 调用登录函数
                response = login()
                # 如果response是元组，取第一个元素（JSON响应）
                if isinstance(response, tuple):
                    data = response[0].get_json()
                else:
                    data = response.get_json()
                
                # 检查结果
                passed = (
                    data['success'] == test['expected']['success'] and
                    data['message'] == test['expected']['message']
                )
                
                results.append({
                    'test_case': test['name'],
                    'passed': passed,
                    'expected': test['expected'],
                    'actual': data
                })
        except Exception as e:
            results.append({
                'test_case': test['name'],
                'passed': False,
                'error': str(e),
                'expected': test['expected'],
                'actual': '测试执行出错'
            })
    
    return render_template('test_results.html', results=results)

# --- 管理后台路由 ---
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('vip'))
        
    if session.get('role') != 'admin':
        return redirect(url_for('vip'))
    
    return render_template('admin/dashboard.html', admin_name=session.get('username', 'Admin'))

# --- 交易策略管理路由 ---
@app.route('/admin/strategy')
def admin_strategy():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('vip'))
    return render_template('admin/strategy.html', admin_name=session.get('username', 'Admin'))

# --- 策略管理API ---
@app.route('/api/admin/strategy', methods=['GET', 'POST', 'DELETE'])
def manage_strategy():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取最新的交易策略
            strategy_response = supabase.table('trading_strategies').select("*").order('updated_at', desc=True).limit(1).execute()
            
            if strategy_response.data:
                strategy = strategy_response.data[0]
                # 确保 trading_focus 是列表格式
                trading_focus = strategy['trading_focus']
                if isinstance(trading_focus, str):
                    try:
                        trading_focus = json.loads(trading_focus)
                    except:
                        trading_focus = [trading_focus]
                        
                return jsonify({
                    'success': True,
                    'strategy': {
                        'id': strategy['id'],
                        'market_analysis': strategy['market_analysis'],
                        'trading_focus': trading_focus,
                        'risk_warning': strategy['risk_warning'],
                        'updated_at': strategy['updated_at']
                    }
                })
            return jsonify({'success': True, 'strategy': None})
            
        elif request.method == 'POST':
            # 创建新策略
            data = request.get_json()
            required_fields = ['market_analysis', 'trading_focus', 'risk_warning']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            # 确保 trading_focus 是列表格式
            trading_focus = data['trading_focus']
            if isinstance(trading_focus, str):
                try:
                    trading_focus = json.loads(trading_focus)
                except:
                    trading_focus = [trading_focus]
                    
            # 插入新策略
            strategy_data = {
                'market_analysis': data['market_analysis'],
                'trading_focus': trading_focus,
                'risk_warning': data['risk_warning'],
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            
            try:
                response = supabase.table('trading_strategies').insert(strategy_data).execute()
                
                if not response.data:
                    return jsonify({'success': False, 'message': 'Creation failed'}), 500
                    
                return jsonify({'success': True, 'message': 'Strategy saved successfully'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'Creation failed: {str(e)}'}), 500
            
        elif request.method == 'DELETE':
            strategy_id = request.args.get('id')
            if not strategy_id:
                return jsonify({'success': False, 'message': '缺少策略ID'}), 400
                
            response = supabase.table('trading_strategies').delete().eq('id', strategy_id).execute()
            
            if not response.data:
                return jsonify({'success': False, 'message': 'Deletion failed'}), 500
                
            return jsonify({'success': True, 'message': 'Strategy deleted successfully'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Operation failed'}), 500

@app.route('/api/admin/strategy/history', methods=['GET'])
def get_strategy_history():
    try:
        # 从 Supabase 获取所有策略记录，按时间倒序排列
        response = supabase.table('trading_strategies').select("*").order('updated_at', desc=True).execute()
        
        if not response.data:
            return jsonify({
                'success': True,
                'history': []
            })
        
        history = []
        for record in response.data:
            # 确保 trading_focus 是列表格式
            trading_focus = record['trading_focus']
            if isinstance(trading_focus, str):
                try:
                    trading_focus = json.loads(trading_focus)
                except:
                    trading_focus = [trading_focus]
                    
            history.append({
                'id': record['id'],
                'market_analysis': record['market_analysis'],
                'trading_focus': trading_focus,
                'risk_warning': record['risk_warning'],
                'modified_at': record['updated_at'],
                'modified_by': 'admin'  # 暂时固定为admin
            })
            
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': '获取历史记录失败'}), 500

@app.route('/admin/strategy/permissions')
def strategy_permissions():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template('admin/strategy_permissions.html', admin_name=session.get('username', 'Admin'))

# --- 删除策略历史记录 ---
@app.route('/api/admin/strategy/history/<int:history_id>', methods=['DELETE'])
def delete_strategy_history(history_id):
    try:
        # 从 Supabase 删除历史记录
        response = supabase.table('strategy_history').delete().eq('id', history_id).execute()
        
        if not response.data:
            return jsonify({'success': False, 'message': '删除失败，记录不存在'}), 404
            
        return jsonify({'success': True, 'message': '历史记录删除成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': '删除失败'}), 500

# --- 股票交易管理路由 ---
@app.route('/admin/trading')
def admin_trading():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('vip'))
    return render_template('admin/trading.html', admin_name=session.get('username', 'Admin'))

# --- 股票交易管理API ---
@app.route('/api/admin/trading', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_trading():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取所有交易记录
            response = supabase.table('trades1').select("*").order('entry_date', desc=True).execute()
            
            trades = []
            for trade in response.data:
                trades.append({
                    'id': trade['id'],
                    'symbol': trade['symbol'],
                    'entry_price': trade['entry_price'],
                    'exit_price': trade.get('exit_price'),
                    'size': trade['size'],
                    'entry_date': trade['entry_date'],
                    'exit_date': trade.get('exit_date'),
                    'status': 'Closed' if trade.get('exit_price') else 'Active',
                    'profit_amount': (trade.get('exit_price', 0) - trade['entry_price']) * trade['size'] if trade.get('exit_price') else 0
                })
                
            return jsonify({
                'success': True,
                'trades': trades
            })
            
        elif request.method == 'POST':
            # 创建新交易记录
            data = request.get_json()
            required_fields = ['symbol', 'entry_price', 'size']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            trade_data = {
                'symbol': data['symbol'],
                'entry_price': data['entry_price'],
                'size': data['size'],
                'entry_date': data.get('entry_date') or datetime.now(pytz.UTC).isoformat(),
                'current_price': data['entry_price']
            }
            
            response = supabase.table('trades1').insert(trade_data).execute()
            
            return jsonify({
                'success': True,
                'message': 'Trade record created successfully'
            })
            
        elif request.method == 'PUT':
            # 更新交易记录
            data = request.get_json()
            trade_id = data.get('id')
            
            if not trade_id:
                return jsonify({'success': False, 'message': '缺少交易ID'}), 400
                
            update_data = {}
            if 'exit_price' in data:
                update_data['exit_price'] = data['exit_price']
                # 使用用户提供的 exit_date，如果没有提供则使用当前时间
                if 'exit_date' in data and data['exit_date']:
                    # 将本地时间转换为 UTC 时间
                    local_date = datetime.fromisoformat(data['exit_date'].replace('Z', '+00:00'))
                    update_data['exit_date'] = local_date.astimezone(pytz.UTC).isoformat()
                else:
                    update_data['exit_date'] = datetime.now(pytz.UTC).isoformat()
                
            if update_data:
                response = supabase.table('trades1').update(update_data).eq('id', trade_id).execute()
                
            return jsonify({
                'success': True,
                'message': 'Trade record updated successfully'
            })
            
        elif request.method == 'DELETE':
            trade_id = request.args.get('id')
            if not trade_id:
                return jsonify({'success': False, 'message': '缺少交易ID'}), 400
                
            response = supabase.table('trades1').delete().eq('id', trade_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'Trade record deleted successfully'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Operation failed'}), 500

# --- 排行榜管理路由 ---
@app.route('/admin/leaderboard')
def admin_leaderboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('vip'))
    return render_template('admin/leaderboard.html', admin_name=session.get('username', 'Admin'))

# --- 排行榜管理API ---
@app.route('/api/admin/leaderboard', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_leaderboard():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取排行榜数据
            response = supabase.table('leaderboard_traders').select("*").order('total_profit', desc=True).execute()
            
            return jsonify({
                'success': True,
                'leaderboard': response.data
            })
            
        elif request.method == 'POST':
            # 添加新的排行榜记录
            data = request.get_json()
            required_fields = ['trader_name', 'total_profit', 'win_rate', 'total_trades', 'profile_image_url']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            leaderboard_data = {
                'trader_name': data['trader_name'],
                'total_profit': data['total_profit'],
                'win_rate': data['win_rate'],
                'total_trades': data['total_trades'],
                'profile_image_url': data['profile_image_url'],
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            
            response = supabase.table('leaderboard_traders').insert(leaderboard_data).execute()
            
            return jsonify({
                'success': True,
                'message': 'Leaderboard record added successfully'
            })
            
        elif request.method == 'PUT':
            # 更新排行榜记录
            data = request.get_json()
            record_id = data.get('id')
            
            if not record_id:
                return jsonify({'success': False, 'message': '缺少记录ID'}), 400
                
            update_data = {
                'trader_name': data.get('trader_name'),
                'total_profit': data.get('total_profit'),
                'win_rate': data.get('win_rate'),
                'total_trades': data.get('total_trades'),
                'profile_image_url': data.get('profile_image_url'),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            
            response = supabase.table('leaderboard_traders').update(update_data).eq('id', record_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'Leaderboard record updated successfully'
            })
            
        elif request.method == 'DELETE':
            record_id = request.args.get('id')
            if not record_id:
                return jsonify({'success': False, 'message': '缺少记录ID'}), 400
                
            response = supabase.table('leaderboard_traders').delete().eq('id', record_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'Leaderboard record deleted successfully'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Operation failed'}), 500

# --- 交易记录表自动建表 ---
def init_trading_db():
    try:
        # 创建交易记录表
        response = supabase.table('trades1').select("*").limit(1).execute()
    except:
        # 如果表不存在，创建表
        supabase.table('trades1').create({
            'id': 'uuid',
            'symbol': 'text',
            'entry_price': 'numeric',
            'exit_price': 'numeric',
            'size': 'numeric',
            'entry_date': 'timestamp with time zone',
            'exit_date': 'timestamp with time zone',
            'current_price': 'numeric',
            'user_id': 'uuid',
            'created_at': 'timestamp with time zone',
            'updated_at': 'timestamp with time zone'
        })

# --- 排行榜表自动建表 ---
def init_leaderboard_db():
    try:
        # 创建排行榜表
        response = supabase.table('leaderboard').select("*").limit(1).execute()
    except:
        # 如果表不存在，创建表
        supabase.table('leaderboard').create({
            'id': 'uuid',
            'user_id': 'uuid',
            'profit': 'numeric',
            'win_rate': 'numeric',
            'total_trades': 'integer',
            'winning_trades': 'integer',
            'losing_trades': 'integer',
            'created_at': 'timestamp with time zone',
            'updated_at': 'timestamp with time zone'
        })

# --- 添加测试数据 ---
def add_test_data():
    try:
        # 添加测试交易记录
        trades_data = [
            {
                'symbol': 'AAPL',
                'entry_price': 150.25,
                'size': 100,
                'entry_date': datetime.now(pytz.UTC).isoformat(),
                'current_price': 155.30,
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            },
            {
                'symbol': 'GOOGL',
                'entry_price': 2750.00,
                'exit_price': 2800.00,
                'size': 10,
                'entry_date': datetime.now(pytz.UTC).isoformat(),
                'exit_date': datetime.now(pytz.UTC).isoformat(),
                'current_price': 2800.00,
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
        ]
        
        # 检查是否已有交易记录
        response = supabase.table('trades1').select("*").execute()
        if not response.data:
            for trade in trades_data:
                supabase.table('trades1').insert(trade).execute()
                
        # 添加测试排行榜数据
        leaderboard_data = [
            {
                'user_id': '1',
                'profit': 15000.00,
                'win_rate': 85.5,
                'total_trades': 100,
                'winning_trades': 85,
                'losing_trades': 15,
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            },
            {
                'user_id': '2',
                'profit': 8500.00,
                'win_rate': 75.0,
                'total_trades': 80,
                'winning_trades': 60,
                'losing_trades': 20,
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
        ]
        
        # 检查是否已有排行榜数据
        response = supabase.table('leaderboard').select("*").execute()
        if not response.data:
            for record in leaderboard_data:
                supabase.table('leaderboard').insert(record).execute()
                
    except Exception as e:
        pass

@app.route('/api/trader/<trader_name>')
def get_trader_data(trader_name):
    try:
        # Get trader data from Supabase
        response = supabase.table('leaderboard_traders')\
            .select('*')\
            .eq('trader_name', trader_name)\
            .single()\
            .execute()
            
        if response.data:
            return jsonify({
                'success': True,
                'trader': response.data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Trader not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error fetching trader data'
        }), 500

@app.route('/api/like-trader/<trader_name>', methods=['POST'])
def like_trader(trader_name):
    try:
        # Get trader data from Supabase
        response = supabase.table('leaderboard_traders')\
            .select('*')\
            .eq('trader_name', trader_name)\
            .single()\
            .execute()
            
        if response.data:
            # Update likes count
            current_likes = response.data.get('likes_count', 0)
            updated_likes = current_likes + 1
            
            # Update in database
            supabase.table('leaderboard_traders')\
                .update({'likes_count': updated_likes})\
                .eq('trader_name', trader_name)\
                .execute()
                
            return jsonify({
                'success': True,
                'likes_count': updated_likes
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Trader not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error updating likes'
        }), 500

@app.route('/api/admin/trade/upload-image', methods=['POST'])
def upload_trade_image():
    try:
        trade_id = request.form.get('trade_id')
        file = request.files.get('image')
        if not trade_id or not file:
            return jsonify({'success': False, 'message': 'Missing trade_id or image'}), 400
        ext = os.path.splitext(secure_filename(file.filename))[1] or '.jpg'
        unique_name = f"avatars/trade_{trade_id}_{uuid.uuid4().hex}{ext}"
        file_bytes = file.read()
        result = supabase.storage.from_('avatars').upload(
            unique_name,
            file_bytes,
            file_options={"content-type": file.content_type}
        )
        file_url = supabase.storage.from_('avatars').get_public_url(unique_name)
        # 自动判断id类型并分表处理
        try:
            int_id = int(trade_id)
            supabase.table('trades1').update({'image_url': file_url}).eq('id', int_id).execute()
        except ValueError:
            supabase.table('trades').update({'image_url': file_url}).eq('id', trade_id).execute()
        return jsonify({'success': True, 'url': file_url})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

@app.route('/api/admin/whatsapp-agents', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_whatsapp_agents():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        if request.method == 'GET':
            # 获取所有WhatsApp客服
            response = supabase.table('whatsapp_agents').select("*").execute()
            return jsonify({
                'success': True,
                'agents': response.data
            })
            
        elif request.method == 'POST':
            # 添加新的WhatsApp客服
            data = request.get_json()
            required_fields = ['name', 'phone_number']
            
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': '缺少必要字段'}), 400
                
            # 验证电话号码格式
            phone_number = data['phone_number']
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
                
            agent_data = {
                'name': data['name'],
                'phone_number': phone_number,
                'is_active': data.get('is_active', True),
                'created_at': datetime.now(pytz.UTC).isoformat(),
                'updated_at': datetime.now(pytz.UTC).isoformat()
            }
            
            response = supabase.table('whatsapp_agents').insert(agent_data).execute()
            
            return jsonify({
                'success': True,
                'message': 'WhatsApp agent added successfully',
                'agent': response.data[0] if response.data else None
            })
            
        elif request.method == 'PUT':
            # 更新WhatsApp客服信息
            data = request.get_json()
            agent_id = data.get('id')
            
            if not agent_id:
                return jsonify({'success': False, 'message': '缺少客服ID'}), 400
                
            update_data = {}
            if 'name' in data:
                update_data['name'] = data['name']
            if 'phone_number' in data:
                phone_number = data['phone_number']
                if not phone_number.startswith('+'):
                    phone_number = '+' + phone_number
                update_data['phone_number'] = phone_number
            if 'is_active' in data:
                update_data['is_active'] = data['is_active']
                
            update_data['updated_at'] = datetime.now(pytz.UTC).isoformat()
            
            response = supabase.table('whatsapp_agents').update(update_data).eq('id', agent_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'WhatsApp agent updated successfully',
                'agent': response.data[0] if response.data else None
            })
            
        elif request.method == 'DELETE':
            # 删除WhatsApp客服
            agent_id = request.args.get('id')
            if not agent_id:
                return jsonify({'success': False, 'message': '缺少客服ID'}), 400
                
            response = supabase.table('whatsapp_agents').delete().eq('id', agent_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'WhatsApp agent deleted successfully'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Operation failed'}), 500

@app.route('/api/upload-trade', methods=['POST'])
def upload_trade():
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        symbol = request.form.get('symbol')
        entry_price = request.form.get('entry_price')
        size = request.form.get('size')
        entry_date = request.form.get('entry_date')
        asset_type = request.form.get('asset_type')
        direction = request.form.get('direction')
        trade_type = request.form.get('trade_type')

        # 检查必填字段
        if not all([user_id, symbol, entry_price, size, entry_date, asset_type, direction]):
            return jsonify({'success': False, 'message': '参数不完整'}), 400

        # 类型转换
        try:
            entry_price = float(entry_price)
            size = float(size)
        except Exception:
            return jsonify({'success': False, 'message': '价格或数量格式错误'}), 400

        resp = supabase.table('trades').insert({
            'user_id': user_id,
            'username': username,
            'symbol': symbol,
            'entry_price': entry_price,
            'size': size,
            'entry_date': entry_date,
            'asset_type': asset_type,
            'direction': direction,
            'trade_type': trade_type
        }).execute()

        # 获取新插入的 trade_id
        trade_id = None
        if resp and hasattr(resp, 'data') and resp.data and isinstance(resp.data, list):
            trade_id = resp.data[0].get('id')

        return jsonify({'success': True, 'message': 'Upload successful', 'trade_id': trade_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/update-trade', methods=['POST'])
def update_trade():
    try:
        trade_id = request.form.get('id')
        exit_price = request.form.get('exit_price')
        exit_date = request.form.get('exit_date')

        print('update trade:', trade_id, exit_price, exit_date)

        if not all([trade_id, exit_price, exit_date]):
            return jsonify({'success': False, 'message': 'Incomplete parameters'}), 400

        try:
            exit_price = float(exit_price)
        except Exception:
            return jsonify({'success': False, 'message': 'Exit price format error'}), 400

        result = supabase.table('trades').update({
            'exit_price': exit_price,
            'exit_date': exit_date
        }).eq('id', trade_id).execute()
        print('update result:', result.data)

        if not result.data:
            return jsonify({'success': False, 'message': 'No record updated, check trade_id or RLS policy.'}), 400

        return jsonify({'success': True, 'message': 'Close position successful'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/change-password', methods=['POST'])
def change_password():
    try:
        user_id = session.get('user_id')
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')

        # 查询用户
        user_resp = supabase.table('users').select('*').eq('id', user_id).execute()
        user = user_resp.data[0] if user_resp.data else None
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 400

        # 检查旧密码
        if old_password != user.get('password_hash'):
            return jsonify({'success': False, 'message': '当前密码错误'}), 400

        # 检查新旧密码是否一样
        if new_password == old_password:
            return jsonify({'success': False, 'message': '新密码不能与旧密码相同'}), 400

        # 更新密码
        supabase.table('users').update({'password_hash': new_password}).eq('id', user_id).execute()
        return jsonify({'success': True, 'message': 'Password changed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/membership-agreement')
def membership_agreement():
    return render_template('membership_agreement.html')

# --- 文档管理API ---
@app.route('/api/admin/documents', methods=['GET', 'POST'])
def manage_documents():
    try:
        if request.method == 'GET':
            response = supabase.table('documents').select('*').order('last_update', desc=True).execute()
            return jsonify({'success': True, 'documents': response.data})
        elif request.method == 'POST':
            file = request.files.get('file')
            title = request.form.get('title')
            description = request.form.get('description')
            now = datetime.now(pytz.UTC).isoformat()
            if not file or not title:
                return jsonify({'success': False, 'message': '标题和文件为必填项'}), 400
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            file_type = file_ext
            bucket = 'documents'
            file_path = f"{uuid.uuid4().hex}_{filename}"
            file_bytes = file.read()
            # 修正上传方式
            result = supabase.storage.from_('documents').upload(
                file_path,
                file_bytes,
                file_options={"content-type": file.mimetype}
            )
            if hasattr(result, 'error') and result.error:
                return jsonify({'success': False, 'message': f'File upload failed: {result.error}'}), 500
            public_url = supabase.storage.from_('documents').get_public_url(file_path)
            doc_data = {
                'title': title,
                'description': description,
                'file_url': public_url,
                'file_type': file_type,
                'last_update': now,
                'views': 0
            }
            insert_resp = supabase.table('documents').insert(doc_data).execute()
            if hasattr(insert_resp, 'error') and insert_resp.error:
                return jsonify({'success': False, 'message': f'Database write failed: {insert_resp.error}'}), 500
            return jsonify({'success': True, 'message': 'Upload successful', 'document': insert_resp.data[0]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/documents/<int:doc_id>', methods=['PUT', 'DELETE'])
def update_document(doc_id):
    try:
        # 权限校验（如有需要可加）
        # if 'role' not in session or session['role'] != 'admin':
        #     return jsonify({'success': False, 'message': '无权限访问'}), 403

        if request.method == 'PUT':
            data = request.get_json()
            update_fields = {k: v for k, v in data.items() if k in ['title', 'description', 'file_url', 'file_type', 'last_update', 'views']}
            if not update_fields:
                return jsonify({'success': False, 'message': '没有可更新的字段'}), 400
            update_fields['last_update'] = datetime.now(pytz.UTC).isoformat()
            resp = supabase.table('documents').update(update_fields).eq('id', doc_id).execute()
            if hasattr(resp, 'error') and resp.error:
                return jsonify({'success': False, 'message': f'Update failed: {resp.error}'}), 500
            return jsonify({'success': True, 'message': 'Update successful'})
        elif request.method == 'DELETE':
            # 先查出 file_url，尝试删除 storage 文件（可选）
            doc_resp = supabase.table('documents').select('file_url').eq('id', doc_id).execute()
            if doc_resp.data and doc_resp.data[0].get('file_url'):
                file_url = doc_resp.data[0]['file_url']
                # 解析出文件名
                try:
                    from urllib.parse import urlparse
                    path = urlparse(file_url).path
                    file_name = path.split('/')[-1]
                    supabase.storage().from_('documents').remove([file_name])
                except Exception as e:
                    pass  # 删除storage失败不影响主流程
            # 删除表记录
            del_resp = supabase.table('documents').delete().eq('id', doc_id).execute()
            if hasattr(del_resp, 'error') and del_resp.error:
                return jsonify({'success': False, 'message': f'Deletion failed: {del_resp.error}'}), 500
            return jsonify({'success': True, 'message': 'Deletion successful'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- 视频管理API ---
@app.route('/api/admin/videos', methods=['GET', 'POST'])
def manage_videos():
    try:
        # 检查用户是否登录
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
            
        if request.method == 'GET':
            # 获取视频列表不需要管理员权限
            response = supabase.table('videos').select('*').order('last_update', desc=True).execute()
            return jsonify({'success': True, 'videos': response.data})
        elif request.method == 'POST':
            # 上传视频需要管理员权限
            if 'role' not in session or session['role'] != 'admin':
                return jsonify({'success': False, 'message': '无权限执行此操作'}), 403
                
            file = request.files.get('file')
            title = request.form.get('title')
            description = request.form.get('description')
            now = datetime.now(pytz.UTC).isoformat()
            
            if not file or not title:
                return jsonify({'success': False, 'message': '标题和视频为必填项'}), 400
                
            # 检查文件大小（限制为600MB）
            file_bytes = file.read()
            if len(file_bytes) > 600 * 1024 * 1024:  # 600MB
                return jsonify({'success': False, 'message': 'File size cannot exceed 600MB'}), 400
                
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            
            # 检查文件类型
            allowed_extensions = {'mp4', 'mov', 'avi', 'wmv', 'flv', 'mkv'}
            if file_ext not in allowed_extensions:
                return jsonify({'success': False, 'message': f'不支持的文件类型，仅支持: {", ".join(allowed_extensions)}'}), 400
            
            file_path = f"{uuid.uuid4().hex}_{filename}"
            
            try:
                # 上传到 Supabase Storage
                result = supabase.storage.from_('videos').upload(
                    file_path,
                    file_bytes,
                    file_options={"content-type": file.mimetype}
                )
                
                if hasattr(result, 'error') and result.error:
                    return jsonify({'success': False, 'message': f'Video upload failed: {result.error}'}), 500
                    
                # 获取公开URL
                public_url = supabase.storage.from_('videos').get_public_url(file_path)
                
                # 写入数据库
                video_data = {
                    'title': title,
                    'description': description,
                    'video_url': public_url,
                    'last_update': now
                }
                
                print("public_url:", public_url)
                print("video_data:", video_data)
                insert_resp = supabase.table('videos').insert(video_data).execute()
                
                if hasattr(insert_resp, 'error') and insert_resp.error:
                    return jsonify({'success': False, 'message': f'Database write failed: {insert_resp.error}'}), 500
                    
                return jsonify({'success': True, 'message': 'Upload successful', 'video': insert_resp.data[0]})
                
            except Exception as e:
                import traceback
                print("视频上传异常：", e)
                print(traceback.format_exc())
                return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500
                
    except Exception as e:
        import traceback
        print("视频上传异常(外层)：", e)
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/videos/<int:video_id>', methods=['PUT', 'DELETE'])
def update_video(video_id):
    try:
        if request.method == 'PUT':
            data = request.get_json()
            update_fields = {k: v for k, v in data.items() if k in ['title', 'description', 'video_url', 'last_update']}
            if not update_fields:
                return jsonify({'success': False, 'message': '没有可更新的字段'}), 400
            update_fields['last_update'] = datetime.now(pytz.UTC).isoformat()
            resp = supabase.table('videos').update(update_fields).eq('id', video_id).execute()
            if hasattr(resp, 'error') and resp.error:
                return jsonify({'success': False, 'message': f'Update failed: {resp.error}'}), 500
            return jsonify({'success': True, 'message': 'Update successful'})
        elif request.method == 'DELETE':
            # 先查出 video_url，尝试删除 storage 文件（可选）
            video_resp = supabase.table('videos').select('video_url').eq('id', video_id).execute()
            if video_resp.data and video_resp.data[0].get('video_url'):
                video_url = video_resp.data[0]['video_url']
                try:
                    from urllib.parse import urlparse
                    path = urlparse(video_url).path
                    file_name = path.split('/')[-1]
                    supabase.storage.from_('videos').remove([file_name])
                except Exception as e:
                    pass  # 删除storage失败不影响主流程
            del_resp = supabase.table('videos').delete().eq('id', video_id).execute()
            if hasattr(del_resp, 'error') and del_resp.error:
                return jsonify({'success': False, 'message': f'Deletion failed: {del_resp.error}'}), 500
            return jsonify({'success': True, 'message': 'Deletion successful'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 默认头像URL和补头像函数
DEFAULT_AVATAR_URL = 'https://via.placeholder.com/150'
def fill_default_avatar(user):
    if not user.get('avatar_url'):
        user['avatar_url'] = DEFAULT_AVATAR_URL
    return user

# 会员等级中英文映射
LEVEL_EN_MAP = {
    '至尊黑卡': 'Supreme Black Card',
    '钻石会员': 'Diamond Member',
    '黄金会员': 'Gold Member',
    '普通会员': 'Regular Member',
    'Supreme Black Card': 'Supreme Black Card',
    'Diamond Member': 'Diamond Member',
    'Gold Member': 'Gold Member',
    'Regular Member': 'Regular Member'
}

def get_level_en(level_cn):
    return LEVEL_EN_MAP.get(level_cn, level_cn)

@app.route('/api/admin/change_avatar', methods=['POST'])
def admin_change_avatar():
    return jsonify({'success': True, 'message': 'Avatar updated successfully', 'avatar_url': DEFAULT_AVATAR_URL})

# 获取所有VIP投资策略公告（Supabase版）
@app.route('/api/admin/vip-announcements', methods=['GET'])
def get_vip_announcements():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        resp = supabase.table('vip_announcements').select('*').order('created_at', desc=True).execute()
        announcements = resp.data if resp.data else []
        return jsonify({'success': True, 'announcements': announcements})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取策略公告失败: {str(e)}'}), 500

# 创建VIP投资策略公告（Supabase版）
@app.route('/api/admin/vip-announcements', methods=['POST'])
def create_vip_announcement():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        data = request.json
        required_fields = ['title', 'content']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': '缺少必要字段'}), 400
            
        # 添加创建者ID和时间戳
        announcement_data = {
            'title': data['title'],
            'content': data['content'],
            'created_by': session['user_id'],
            'status': data.get('status', 'active'),
            'priority': data.get('priority', 0)
        }
        
        resp = supabase.table('vip_announcements').insert(announcement_data).execute()
        if hasattr(resp, 'error') and resp.error:
            return jsonify({'success': False, 'message': f'创建失败: {resp.error}'}), 500
            
        return jsonify({'success': True, 'message': '策略公告已创建'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建策略公告失败: {str(e)}'}), 500

# 编辑VIP投资策略公告（Supabase版）
@app.route('/api/admin/vip-announcements/<int:announcement_id>', methods=['PUT'])
def edit_vip_announcement(announcement_id):
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        data = request.json
        # 允许更新所有在截图中出现的字段
        update_fields = {k: v for k, v in data.items() if k in ['title', 'content', 'status', 'priority', 'type', 'publisher', 'date']}
        if not update_fields:
            return jsonify({'success': False, 'message': '没有可更新的字段'}), 400
            
        resp = supabase.table('vip_announcements').update(update_fields).eq('id', announcement_id).execute()
        
        # 检查更新是否成功
        if hasattr(resp, 'data') and resp.data:
            return jsonify({'success': True, 'message': '策略公告已更新'})
        else:
            # 分析可能的错误
            error_message = '更新失败'
            if hasattr(resp, 'error') and resp.error:
                error_message += f": {resp.error.message}"
            return jsonify({'success': False, 'message': error_message}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新策略公告失败: {str(e)}'}), 500

# 删除VIP投资策略公告（Supabase版）
@app.route('/api/admin/vip-announcements/<int:announcement_id>', methods=['DELETE'])
def delete_vip_announcement(announcement_id):
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        resp = supabase.table('vip_announcements').delete().eq('id', announcement_id).execute()
        if hasattr(resp, 'error') and resp.error:
            return jsonify({'success': False, 'message': f'删除失败: {resp.error}'}), 500
            
        return jsonify({'success': True, 'message': '策略公告已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除策略公告失败: {str(e)}'}), 500

# 获取所有VIP交易记录（Supabase版）
@app.route('/api/admin/vip-trades', methods=['GET'])
def get_vip_trades():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        resp = supabase.table('vip_trades').select('*').order('entry_time', desc=True).execute()
        trades = resp.data if resp.data else []
        
        for trade in trades:
            # 获取最新 current_price
            current_price = trade.get('current_price')
            entry_price = float(trade.get('entry_price') or 0)
            quantity = float(trade.get('quantity') or 0)
            current_price = float(current_price or 0)
            direction = str(trade.get('direction', '')).lower()
            if entry_price and quantity:
                if direction in ['买涨', 'buy', '多', 'long']:
                    pnl = (current_price - entry_price) * quantity
                elif direction in ['买跌', 'sell', '空', 'short']:
                    pnl = (entry_price - current_price) * quantity
                else:
                    pnl = (current_price - entry_price) * quantity
                roi = (pnl / (entry_price * quantity)) * 100
            else:
                pnl = 0
                roi = 0
            # 写入数据库
            supabase.table('vip_trades').update({
                'pnl': pnl,
                'roi': roi
            }).eq('id', trade['id']).execute()
            trade['pnl'] = pnl
            trade['roi'] = roi
        
        return jsonify({
            'success': True,
            'trades': trades
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取交易记录失败: {str(e)}'}), 500

# 新增VIP交易记录（Supabase版）
@app.route('/api/admin/vip-trades', methods=['POST'])
def add_vip_trade():
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        data = request.json
        required_fields = ['symbol', 'entry_price', 'quantity', 'entry_time', 'trade_type']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': '缺少必要字段'}), 400
            
        # 验证数据类型
        try:
            entry_price = float(data['entry_price'])
            quantity = float(data['quantity'])
            entry_time = datetime.fromisoformat(data['entry_time'].replace('Z', '+00:00'))
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'message': f'数据类型错误: {str(e)}'}), 400
            
        # 获取当前价格
        current_price = get_real_time_price(data['symbol'])
        if not current_price:
            return jsonify({'success': False, 'message': '无法获取当前价格'}), 400
            
        # 计算初始盈亏
        pnl = (current_price - entry_price) * quantity
        roi = (pnl / (entry_price * quantity)) * 100 if entry_price and quantity else 0
        
        # 准备交易数据
        trade_data = {
            'symbol': data['symbol'],
            'entry_price': entry_price,
            'quantity': quantity,
            'entry_time': entry_time.isoformat(),
            'trade_type': data['trade_type'],
            'status': 'open',
            'current_price': current_price,
            'pnl': pnl,
            'roi': roi,
            'created_by': session['user_id'],
            'asset_type': data.get('asset_type'),  # 新增
            'direction': data.get('direction')     # 新增
        }
        
        resp = supabase.table('vip_trades').insert(trade_data).execute()
        if hasattr(resp, 'error') and resp.error:
            return jsonify({'success': False, 'message': f'创建失败: {resp.error}'}), 500
            
        return jsonify({'success': True, 'message': '交易记录已添加'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加交易记录失败: {str(e)}'}), 500

# 编辑VIP交易记录（Supabase版）
@app.route('/api/admin/vip-trades/<int:trade_id>', methods=['PUT'])
def edit_vip_trade(trade_id):
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        data = request.json
        update_fields = {k: v for k, v in data.items() if k in [
            'symbol', 'entry_price', 'exit_price', 'quantity', 
            'entry_time', 'exit_time', 'trade_type', 'status', 
            'notes', 'asset_type', 'direction'  # 新增
        ]}
        
        if not update_fields:
            return jsonify({'success': False, 'message': '没有可更新的字段'}), 400
            
        # 如果更新了价格相关字段，重新计算盈亏
        if any(k in update_fields for k in ['entry_price', 'exit_price', 'quantity']):
            current_price = get_real_time_price(update_fields.get('symbol', data.get('symbol')))
            if current_price:
                entry_price = float(update_fields.get('entry_price', data.get('entry_price', 0)))
                quantity = float(update_fields.get('quantity', data.get('quantity', 0)))
                pnl = (current_price - entry_price) * quantity
                roi = (pnl / (entry_price * quantity)) * 100 if entry_price and quantity else 0
                
                update_fields.update({
                    'current_price': current_price,
                    'pnl': pnl,
                    'roi': roi
                })
        
        resp = supabase.table('vip_trades').update(update_fields).eq('id', trade_id).execute()
        if hasattr(resp, 'error') and resp.error:
            return jsonify({'success': False, 'message': f'更新失败: {resp.error}'}), 500
            
        return jsonify({'success': True, 'message': '交易记录已更新'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新交易记录失败: {str(e)}'}), 500

# 删除VIP交易记录（Supabase版）
@app.route('/api/admin/vip-trades/<int:trade_id>', methods=['DELETE'])
def delete_vip_trade(trade_id):
    try:
        # 检查管理员权限
        if 'role' not in session or session['role'] != 'admin':
            return jsonify({'success': False, 'message': '无权限访问'}), 403
            
        resp = supabase.table('vip_trades').delete().eq('id', trade_id).execute()
        if hasattr(resp, 'error') and resp.error:
            return jsonify({'success': False, 'message': f'删除失败: {resp.error}'}), 500
            
        return jsonify({'success': True, 'message': '交易记录已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除交易记录失败: {str(e)}'}), 500

@app.route('/download-proxy')
def download_proxy():
    url = request.args.get('url')
    if not url:
        return 'Missing url', 400
    r = requests.get(url, stream=True)
    filename = url.split('/')[-1]
    return Response(
        r.iter_content(chunk_size=8192),
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': r.headers.get('Content-Type', 'application/octet-stream')
        }
    )

@app.route('/api/admin/trader-profiles', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_trader_profiles():
    """管理交易员档案的API端点"""
    try:
        if request.method == 'GET':
            # 获取所有交易员档案
            response = supabase.table('trader_profiles').select("*").execute()
            return jsonify({
                'success': True,
                'data': response.data
            })
        
        elif request.method == 'POST':
            # 创建新的交易员档案
            data = request.json
            required_fields = ['trader_name', 'professional_title']
            
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'message': f'Missing required field: {field}'
                    }), 400
            
            # 设置默认值
            data['created_at'] = datetime.now(pytz.UTC).isoformat()
            data['updated_at'] = datetime.now(pytz.UTC).isoformat()
            
            response = supabase.table('trader_profiles').insert(data).execute()
            
            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Trader profile created successfully',
                    'data': response.data[0]
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create trader profile'
                }), 500
        
        elif request.method == 'PUT':
            # 更新交易员档案
            data = request.json
            profile_id = data.get('id')
            
            if not profile_id:
                return jsonify({
                    'success': False,
                    'message': 'Missing profile ID'
                }), 400
            
            # 更新时间戳
            data['updated_at'] = datetime.now(pytz.UTC).isoformat()
            
            response = supabase.table('trader_profiles').update(data).eq('id', profile_id).execute()
            
            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Trader profile updated successfully',
                    'data': response.data[0]
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to update trader profile'
                }), 500
        
        elif request.method == 'DELETE':
            # 删除交易员档案
            profile_id = request.args.get('id')
            
            if not profile_id:
                return jsonify({
                    'success': False,
                    'message': 'Missing profile ID'
                }), 400
            
            response = supabase.table('trader_profiles').delete().eq('id', profile_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'Trader profile deleted successfully'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/admin/trader-profiles')
def admin_trader_profiles():
    """交易员档案管理页面"""
    return render_template('admin/trader_profiles.html')

@app.route('/api/admin/clear-avatars', methods=['POST'])
def clear_avatars():
    """清空所有交易员档案的头像数据"""
    try:
        # 先获取所有记录
        response = supabase.table('trader_profiles').select('id').execute()
        if response.data:
            # 逐个更新每个记录
            for record in response.data:
                supabase.table('trader_profiles').update({
                    'profile_image_url': None
                }).eq('id', record['id']).execute()
        
        return jsonify({
            'success': True,
            'message': '所有头像数据已清空'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清空失败: {str(e)}'
        }), 500

@app.route('/api/admin/update-trader-avatar/<int:trader_id>', methods=['POST'])
def update_trader_avatar(trader_id):
    """更新特定交易员的头像"""
    try:
        # 将指定交易员的头像设为null
        response = supabase.table('trader_profiles').update({
            'profile_image_url': None
        }).eq('id', trader_id).execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': f'交易员 {trader_id} 的头像已清空'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'交易员 {trader_id} 不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    # 初始化数据库
    init_user_db()
    init_membership_levels_db()
    init_user_membership_db()
    
    # 启动应用 - 使用环境变量中的端口，默认为 8000
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
