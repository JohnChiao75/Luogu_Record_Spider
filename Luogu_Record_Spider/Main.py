import webview
import asyncio
import threading
import json
import os
import time
from datetime import datetime, timedelta
from Get_Cookies import Recent_Login, Get_New_Cookies
from Get_Record import schedule_monitoring

# ==========================================
# --- 1. 配置区域 ---
# ==========================================

# 修正后的颜色配置
DIFFICULTY_COLORS = {
    "入门": "#fe4c61",
    "普及−": "#f39c11",
    "普及/提高−": "#ffc116",
    "普及+/提高": "#53c41a",
    "提高+/省选": "#3498db",
    "省选/NOI−": "#9c3dcf",
    "NOI/NOI+/CTSC": "#0e1d69"
}
DEFAULT_COLOR = "#bfbfbf"

# 难度等级映射（用于筛选范围）
DIFFICULTY_LEVELS = {
    "入门": 0,
    "普及−": 1,
    "普及/提高−": 2,
    "普及+/提高": 3,
    "提高+/省选": 4,
    "省选/NOI−": 5,
    "NOI/NOI+/CTSC": 6
}
# 反向映射用于前端下拉框生成
LEVELS_TO_NAME = {v: k for k, v in DIFFICULTY_LEVELS.items()}

# 桌面右下角弹窗模板 (颜色已更新)
TOAST_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0; padding: 0; overflow: hidden;
            background-color: #fff; font-family: 'Segoe UI', sans-serif;
            border-left: 8px solid {color};
            display: flex; flex-direction: column; justify-content: center;
            height: 100vh; padding-left: 15px; box-sizing: border-box;
            user-select: none; cursor: default;
        }}
        .header {{ font-size: 12px; color: #888; margin-bottom: 5px; display: flex; justify-content: space-between; padding-right: 15px;}}
        .user {{ font-weight: bold; color: #333; font-size: 14px; }}
        .content {{ font-size: 13px; color: #444; margin-bottom: 8px; line-height: 1.4; padding-right: 10px;}}
        .problem-id {{ font-weight: bold; color: #000; }}
        .badge {{
            display: inline-block; background-color: {color}; color: white;
            padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;
        }}
        .close-btn {{
            position: absolute; top: 5px; right: 8px; color: #ccc; cursor: pointer; font-size: 16px;
        }}
        .close-btn:hover {{ color: #000; }}
    </style>
</head>
<body>
    <div class="close-btn" onclick="closeMe()">×</div>
    <div class="header">
        <span class="user">{user_name}</span>
        <span>{time_str}</span>
    </div>
    <div class="content">
        提交了 <span class="problem-id">{problem_number}</span><br>
        {problem_name}
    </div>
    <div>
        <span class="badge">{difficulty}</span>
    </div>
    <script>
        function closeMe() {{ pywebview.api.close_toast(); }}
        setTimeout(closeMe, 8000);
    </script>
</body>
</html>
"""

# ==========================================
# --- 独立弹窗 API ---
# ==========================================
class ToastApi:
    def __init__(self, window):
        self.window = window
    def close_toast(self):
        self.window.destroy()

# ==========================================
# --- 主程序 API ---
# ==========================================
class Api:
    def __init__(self):
        self._window = None
        self.loop = None
        self.monitor_task = None
        self.current_username = None 
        self.notified_records = set() 
        self.monitoring_active = False 

    def set_window(self, window):
        self._window = window

    # --- 基础功能 ---
    def init_check(self):
        user = Recent_Login()
        if user == "Not_Found_User":
            return {"status": "require_login"}
        else:
            self.current_username = user
            return {"status": "success", "username": user}

    def attempt_login(self, username, password):
        success = asyncio.run(Get_New_Cookies(username, password))
        if success:
            self.current_username = username
            return {"status": "success", "username": username}
        else:
            return {"status": "fail", "message": "用户名或密码错误"}

    # --- 监控逻辑 ---
    def start_monitoring(self, username):
        print(f"[系统] 准备启动监控: {username}")
        self.stop_monitoring()
        self.monitoring_active = True 

        # 线程1: 爬虫
        def crawler_thread_target():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            self.loop = new_loop
            self.monitor_task = new_loop.create_task(schedule_monitoring(username, 0.5))
            try:
                new_loop.run_until_complete(self.monitor_task)
            except: pass
            finally:
                if new_loop.is_running(): new_loop.stop()
                new_loop.close()

        # 线程2: 通知检测
        def notification_checker_target():
            print("[系统] 弹窗检测服务已启动")
            while self.monitoring_active:
                try:
                    self.check_and_notify()
                except Exception as e:
                    print(f"[错误] 检测通知出错: {e}")
                time.sleep(10)

        t1 = threading.Thread(target=crawler_thread_target, daemon=True)
        t1.start()
        t2 = threading.Thread(target=notification_checker_target, daemon=True)
        t2.start()

    def stop_monitoring(self):
        self.monitoring_active = False
        if self.loop and self.monitor_task:
            try:
                self.loop.call_soon_threadsafe(self.monitor_task.cancel)
            except RuntimeError: pass
            self.loop = None
            self.monitor_task = None

    def check_and_notify(self):
        problem_map = self._load_json('problem_list.json')
        users_data = self._load_json('user_records.json')
        if not users_data: return

        now = datetime.now()

        for user in users_data:
            uid = user.get('user_id')
            uname = user.get('user_name')
            for record in user.get('records', []):
                p_num = record.get('problem_number')
                p_name = record.get('problem_name')
                post_date_str = record.get('post_date')
                
                record_id = f"{uid}_{p_num}_{post_date_str}"
                
                if record_id in self.notified_records: continue
                
                try:
                    record_time = datetime.strptime(post_date_str, "%Y-%m-%d %H:%M:%S")
                    if now - record_time < timedelta(minutes=10):
                        self.notified_records.add(record_id)
                        
                        difficulty = problem_map.get(p_num, "未知")
                        color = DIFFICULTY_COLORS.get(difficulty, DEFAULT_COLOR)
                        time_display = post_date_str.split(" ")[1]

                        # 1. 桌面弹窗
                        self.show_desktop_toast(uname, p_num, p_name, time_display, difficulty, color)

                        # 2. 应用内弹窗
                        notify_data = {
                            "user_name": uname, "problem_number": p_num, "problem_name": p_name,
                            "time_str": time_display, "difficulty": difficulty, "color": color
                        }
                        if self._window:
                            self._window.evaluate_js(f'createNotificationCard({json.dumps(notify_data)})')
                        
                        time.sleep(1) 
                except ValueError: continue

    def show_desktop_toast(self, uname, p_num, p_name, t_str, diff, col):
        screens = webview.screens
        if not screens: return
        screen = screens[0]
        width, height = 300, 140
        x = int(screen.width - width - 20)
        y = int(screen.height - height - 60)

        html = TOAST_HTML_TEMPLATE.format(
            user_name=uname, problem_number=p_num, problem_name=p_name,
            time_str=t_str, difficulty=diff, color=col
        )
        toast = webview.create_window(
            title='Notification', html=html, width=width, height=height,
            x=x, y=y, frameless=True, on_top=True, resizable=False, focus=False
        )
        toast.expose(ToastApi(toast).close_toast)

    # ==========================================
    # --- 3. 数据查询与排行榜功能 (新增) ---
    # ==========================================

    def _load_json(self, filename):
        if not os.path.exists(filename): return {} if 'list' in filename else []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {} if 'list' in filename else []

    def get_leaderboard_data(self, days, min_lv, max_lv):
        """获取排行榜数据"""
        try:
            days = int(days)
            if days > 60: days = 60 # 限制最大60天
            min_lv = int(min_lv)
            max_lv = int(max_lv)
        except:
            return {"status": "error", "message": "参数错误"}

        users_data = self._load_json('user_records.json')
        problem_map = self._load_json('problem_list.json')
        
        now = datetime.now()
        start_date = now - timedelta(days=days)
        
        leaderboard = []

        for user in users_data:
            valid_count = 0
            uid = user.get('user_id')
            uname = user.get('user_name')
            
            for record in user.get('records', []):
                # 1. 时间筛选
                p_date_str = record.get('post_date')
                try:
                    p_date = datetime.strptime(p_date_str, "%Y-%m-%d %H:%M:%S")
                    if p_date < start_date: continue
                except: continue

                # 2. 难度筛选
                p_num = record.get('problem_number')
                difficulty = problem_map.get(p_num, "未知")
                
                # 如果是未知难度，通常不计入等级筛选，或者你可以决定是否计入
                # 这里假设只统计有明确等级的题目
                level = DIFFICULTY_LEVELS.get(difficulty, -1)
                
                if level != -1 and min_lv <= level <= max_lv:
                    valid_count += 1
            
            if valid_count > 0:
                leaderboard.append({
                    "user_id": uid,
                    "user_name": uname,
                    "count": valid_count
                })

        # 排序
        leaderboard.sort(key=lambda x: x['count'], reverse=True)
        return {"status": "success", "data": leaderboard}

    def get_user_records_page(self, uid, page, page_size=10):
        """获取单个用户的详细记录（分页）"""
        users_data = self._load_json('user_records.json')
        problem_map = self._load_json('problem_list.json')
        
        target_user = next((u for u in users_data if str(u.get('user_id')) == str(uid)), None)
        
        if not target_user:
            return {"status": "error", "message": "用户未找到"}
        
        all_records = target_user.get('records', [])
        total = len(all_records)
        
        # 计算分页
        start = (page - 1) * page_size
        end = start + page_size
        paged_records = all_records[start:end]
        
        # 补充难度颜色信息
        processed_records = []
        for r in paged_records:
            p_num = r.get('problem_number')
            diff = problem_map.get(p_num, "未知")
            color = DIFFICULTY_COLORS.get(diff, DEFAULT_COLOR)
            
            r_copy = r.copy()
            r_copy['difficulty'] = diff
            r_copy['color'] = color
            processed_records.append(r_copy)
            
        return {
            "status": "success",
            "data": processed_records,
            "total": total,
            "user_name": target_user.get('user_name')
        }

    # ==========================================
    # --- 4. 配置管理 (增强) ---
    # ==========================================
    
    def _get_current_uid(self):
        if not self.current_username: return None
        data = self._load_json('cookies.json')
        if isinstance(data, list):
            for u in data:
                if u.get('user_name') == self.current_username: return u.get('user_id')
        return None

    def get_monitor_config(self):
        uid = self._get_current_uid()
        if not uid: return {"status": "error", "message": "User not found"}
        
        monitor_list = [] # 仅包含 ID 的列表
        try:
            user_ids_data = self._load_json('user_ids.json')
            monitor_list = user_ids_data.get(str(uid), [])
        except: pass
        
        # --- 增强：匹配用户名 ---
        users_records = self._load_json('user_records.json')
        # 创建 ID -> Name 映射
        id_name_map = {str(u['user_id']): u['user_name'] for u in users_records}
        
        enhanced_list = []
        for m_uid in monitor_list:
            name = id_name_map.get(str(m_uid), "未知用户")
            enhanced_list.append({"id": str(m_uid), "name": name})
            
        return {"status": "success", "data": enhanced_list, "current_uid": uid}

    def save_monitor_config(self, new_list):
        # new_list 只是 ID 的列表
        uid = self._get_current_uid()
        if not uid: return {"status": "error", "message": "Auth failed"}
        
        data = self._load_json('user_ids.json')
        if isinstance(data, list): data = {} # 防错
        
        data[str(uid)] = new_list
        try:
            with open('user_ids.json', 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
        except Exception as e: return {"status": "error", "message": str(e)}
        
        print(f"[系统] 配置更新，重启监控...")
        self.start_monitoring(self.current_username)
        return {"status": "success"}

    # --- 其他 ---
    def logout(self):
        self.stop_monitoring()
        self.current_username = None
        return {"status": "logged_out"}
    def close_app(self): self._window.destroy()

if __name__ == '__main__':
    api = Api() 
    window = webview.create_window(
        'Luogu Monitor Pro', 'web/index.html',
        width=950, height=800, # 稍微调大一点适应排行榜
        resizable=False, js_api=api, frameless=True, easy_drag=True
    )
    api.set_window(window)
    webview.start(debug=False)
