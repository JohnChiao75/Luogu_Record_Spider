import asyncio
import json
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright,expect

async def visit_user_record_list(context, user_id, max_pages=5, existing_records_path="user_records.json", days_threshold=60):
    """
    访问单个用户的记录列表页面并提取数据
    
    参数:
        context: 浏览器上下文对象
        user_id: 用户ID
        max_pages: 最大爬取页数
        existing_records_path: 已存在记录文件路径
        days_threshold: 时间阈值（天），超过这个天数的记录停止爬取
    
    功能:
        1. 打开新页面访问用户记录页面
        2. 循环提取多页记录内容
        3. 根据停止条件提前结束爬取
    """
    # 创建新页面
    page = await context.new_page()
    
    user_record = []
    user_name = ""
    table_head = ["post_date", "problem_number", "problem_name"]
    
    # 加载已存在的记录
    existing_records = []
    try:
        with open(existing_records_path, "r", encoding="utf-8") as file:
            existing_data = json.load(file)
            # 查找当前用户的已存在记录
            for user_data in existing_data:
                if user_data.get("user_id") == user_id:
                    existing_records = user_data.get("records", [])
                    break
    except (FileNotFoundError, json.JSONDecodeError):
        existing_records = []
    
    # 将已存在记录转换为集合以便快速查找
    existing_record_set = set()
    for record in existing_records:
        # 使用题目编号和提交日期作为唯一标识
        record_key = f"{record.get('problem_number', '')}_{record.get('post_date', '')}"
        existing_record_set.add(record_key)

    new_existing_record_set = set()
    
    # 计算日期阈值
    threshold_date = datetime.now() - timedelta(days=days_threshold)
    
    # 爬取多页数据
    should_stop = False
    
    for page_num in range(1, max_pages + 1):
        if should_stop:
            break
            
        # 构建用户记录页面URL
        url = f"https://www.luogu.com.cn/record/list?user={user_id}&status=12&page={page_num}"
        await page.goto(url)
        print(f"已访问用户 {user_id} 第 {page_num} 页")
        
        # 等待页面加载
        await page.wait_for_timeout(1000)
        
        # 检查是否有记录
        try:
            # 检查是否有记录容器
            record_container = page.locator('//*[@id="app"]/div[2]/main/div/div/div/div[1]/div')
            record_count = await record_container.count()
            
            if record_count == 0:
                print(f"用户 {user_id} 第 {page_num} 页没有记录")
                break
            
            # 检查是否显示"暂时没有符合该筛选条件的提交记录"
            try:
                no_record_text = await page.locator('//*[@id="app"]/div[2]/main/div/div/div/div[2]').text_content()
                if "暂时没有符合该筛选条件的提交记录" in no_record_text:
                    print(f"用户 {user_id} 没有提交记录")
                    break
            except:
                pass
                
            # 循环提取当前页的记录（最多20条）
            page_records = 0
            for i in range(1, 21):  # 每页最多20条记录
                if should_stop:
                    break
                    
                try:
                    # 尝试定位第i条记录
                    record_locator = page.locator(f'//*[@id="app"]/div[2]/main/div/div/div/div[1]/div/div[{i}]')
                    await expect(record_locator).to_be_visible()
                    # 检查元素是否存在
                    count = await record_locator.count()
                    if count == 0:
                        break  # 没有更多记录了
                        
                    text = await record_locator.text_content()
                    
                    # 按换行符分割文本
                    format_text = text.split("\n")
                    
                    # 检查是否有足够的数据
                    if len(format_text) >= 10:
                        if page_num == 1 and i == 1:  # 只在第一页第一条记录获取用户名
                            user_name = format_text[1][2:] if len(format_text[1]) > 2 else "未知用户"
                        
                        post_date_str = format_text[3][12:] if len(format_text[3]) > 12 else ""
                        if post_date_str.count("-") == 1:
                            post_date_str = str(datetime.now().year) + "-" + post_date_str
                        else:
                            post_date_str = post_date_str + ":00"

                        problem_number = format_text[8][4:] if len(format_text[8]) > 4 else ""

                        problem_name = format_text[9][4:] if len(format_text[9]) > 4 else ""
                        
                        # 检查日期是否超过阈值
                        if post_date_str:
                            try:
                                record_date = datetime.strptime(post_date_str, "%Y-%m-%d %H:%M:%S")
                                
                                # 检查是否超过60天
                                if record_date < threshold_date:
                                    print(f"用户 {user_id} 记录 {post_date_str} 超过 {days_threshold} 天，停止爬取")
                                    should_stop = True
                                    break
                            except ValueError:
                                print(f"用户 {user_id} 记录日期格式异常: {post_date_str}")
                        
                        # 检查记录是否已存在
                        record_key = f"{problem_number}_{post_date_str}"
                        if record_key in existing_record_set:
                            print(f"用户 {user_id} 记录 {record_key} 已存在，停止爬取")
                            should_stop = True
                            break
                        
                        # 创建记录字典（保持原有格式）
                        table_content = [post_date_str, problem_number, problem_name]
                        record_dict = dict(zip(table_head, table_content))
                        
                        user_record.append(record_dict)
                        page_records += 1
                        
                        # 将新记录添加到已存在记录集合，避免同一页面内重复
                        new_existing_record_set.add(record_key)
                        
                        # 每条记录等待0.05秒（原代码逻辑）
                        await page.wait_for_timeout(0.05)
                    else:
                        # 修改为更友好的提示
                        print(f"用户 {user_id} 第 {page_num} 页第 {i} 条记录数据不完整，跳过")
                        
                except Exception as e:
                    # 修改为更友好的提示
                    print(f"用户 {user_id} 第 {page_num} 页第 {i} 条记录获取失败，跳过")
                    continue
            
            print(f"用户 {user_id} 第 {page_num} 页爬取了 {page_records} 条记录")
            
            # 如果当前页记录少于20条，可能没有下一页了
            if page_records < 20:
                break
                
        except Exception as e:
            print(f"用户 {user_id} 第 {page_num} 页访问失败: {str(e)[:50]}")
            break
    
    existing_record_set.update(new_existing_record_set)
    await page.wait_for_timeout(500)
    # 最后等待0.5秒
    
    # 关闭页面
    await page.close()

    return {"user_id": user_id, "user_name": user_name, "records": user_record}

async def create_browser_context(login_user_id, cookie_path="cookies.json", headless=True):
    """
    创建浏览器上下文并加载cookies
    
    参数:
        cookie_path: cookies.json文件路径
        headless: 是否无头模式
    
    返回:
        tuple: (playwright实例, browser实例, context实例)
    """
    # 读取cookies文件
    with open(cookie_path, "r") as file:
        cookies = json.load(file)

    # 将cookies转换为Playwright格式
    for i in range(len(cookies)):
        if cookies[i].get("user_id") == login_user_id:
            cookies_list = cookies[i].get("cookies")
    
    # 启动Playwright和浏览器
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    
    # 创建上下文并添加cookies
    context = await browser.new_context()
    await context.add_cookies(cookies_list)
    
    return p, browser, context

async def run_spider(login_user_id, user_ids, cookie_path="cookies.json", max_pages_per_user=10, existing_records_path="user_records.json", days_threshold=60):
    """
    主爬虫执行函数
    
    参数:
        login_user_id：登录的用户ID
        user_ids: 用户ID列表
        cookie_path: cookies.json文件路径
        max_pages_per_user: 每个用户最大爬取页数
        existing_records_path: 已存在记录文件路径
        days_threshold: 时间阈值（天），超过这个天数的记录停止爬取
    
    流程:
        1. 创建浏览器上下文
        2. 为每个用户ID创建异步任务（每10个用户一组）
        3. 并行执行每组任务，组间串行执行
        4. 清理资源
    
    返回:
        list: 爬取的用户记录列表
    """
    # 初始化变量
    p, browser, context = None, None, None
    
    try:
        # 1. 创建浏览器上下文
        
        p, browser, context = await create_browser_context(login_user_id, cookie_path, headless=True)
        
        # 所有用户的结果
        all_user_record_list = []
        
        # 2. 分批处理用户列表（每10个用户一组）
        for i in range(0, len(user_ids), 10):
            # 获取当前批次的用户ID
            batch_user_ids = user_ids[i:i+10]
            print(f"正在爬取第 {i//10 + 1} 批用户，共 {len(batch_user_ids)} 个用户")
            print(f"每用户最多 {max_pages_per_user} 页，时间阈值 {days_threshold} 天")
            
            # 2. 创建任务列表（当前批次）
            tasks = []
            for user_id in batch_user_ids:
                # 为每个用户创建异步任务，传递停止条件参数
                task = asyncio.create_task(
                    visit_user_record_list(
                        context, 
                        user_id, 
                        max_pages_per_user,
                        existing_records_path,
                        days_threshold
                    )
                )
                tasks.append(task)
            
            # 3. 并行执行当前批次的所有任务
            batch_results = await asyncio.gather(*tasks)
            all_user_record_list.extend(batch_results)
            
            print(f"第 {i//10 + 1} 批用户爬取完成")
            
            # 如果不是最后一批，等待一下再开始下一批
            if i + 10 < len(user_ids):
                await asyncio.sleep(1)  # 批次间等待1秒

        return all_user_record_list
        
    finally:
        # 4. 确保资源被清理（即使出错）
        if context:
            await context.close()
        if browser:
            await browser.close()
        if p:
            await p.stop()

def merge_records(existing_records, new_records):
    """
    合并新旧记录，避免重复
    
    参数:
        existing_records: 已存在的记录列表
        new_records: 新爬取的记录列表
    
    返回:
        list: 合并后的记录列表
    """
    # 如果没有旧记录，直接返回新记录
    if not existing_records:
        return new_records
    
    # 创建用户ID到记录的映射
    user_records_map = {}
    
    # 首先加载所有已存在的记录
    for record in existing_records:
        user_id = record["user_id"]
        user_records_map[user_id] = {
            "user_id": user_id,
            "user_name": record["user_name"],
            "records": record["records"]
        }
    
    # 然后合并新记录
    for new_record in new_records:
        user_id = new_record["user_id"]
        
        # 如果用户已存在，合并记录
        if user_id in user_records_map:
            existing_record_set = set()
            existing_records_list = user_records_map[user_id]["records"]
            
            # 将已有记录转换为集合以便快速查找
            for record in existing_records_list:
                record_key = f"{record.get('problem_number', '')}_{record.get('post_date', '')}"
                existing_record_set.add(record_key)
            
            # 添加新记录（如果不存在）
            for record in new_record["records"]:
                record_key = f"{record.get('problem_number', '')}_{record.get('post_date', '')}"
                if record_key not in existing_record_set:
                    existing_records_list.append(record)
                    existing_record_set.add(record_key)
            
            # 更新用户名（如果有新用户名）
            if new_record["user_name"] and new_record["user_name"] != "未知用户":
                user_records_map[user_id]["user_name"] = new_record["user_name"]
        else:
            # 新用户，直接添加
            user_records_map[user_id] = new_record
    
    # 转换回列表
    merged_records = list(user_records_map.values())
    
    # 对每个用户的记录按时间倒序排序（最新的在前面）
    for record in merged_records:
        if record["records"]:
            try:
                record["records"].sort(
                    key=lambda x: datetime.strptime(x["post_date"], "%Y-%m-%d %H:%M:%S") if x["post_date"] else datetime.min,
                    reverse=True
                )
            except:
                pass
    
    return merged_records

def clean_old_records(records, days_threshold=60):
    """
    清理60天以前的旧记录
    
    参数:
        records: 用户记录列表
        days_threshold: 时间阈值（天）
    
    返回:
        list: 清理后的记录列表
    """
    if not records:
        return records
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days_threshold)
    
    # 统计清理前的记录总数
    total_before = sum(len(user["records"]) for user in records)
    removed_count = 0
    
    # 清理每个用户的旧记录
    cleaned_records = []
    for user_data in records:
        user_id = user_data["user_id"]
        old_records = user_data["records"]
        
        # 过滤掉60天以前的记录
        new_records = []
        for record in old_records:
            try:
                record_date = datetime.strptime(record["post_date"], "%Y-%m-%d %H:%M:%S")
                if record_date >= cutoff_date:
                    new_records.append(record)
                else:
                    removed_count += 1
            except (ValueError, KeyError):
                # 如果日期格式错误，保留记录
                new_records.append(record)
        
        # 只保留有记录的用户
        if new_records:
            cleaned_records.append({
                "user_id": user_id,
                "user_name": user_data["user_name"],
                "records": new_records
            })
    
    # 统计清理后的记录总数
    total_after = sum(len(user["records"]) for user in cleaned_records)
    
    print(f"清理旧记录：移除了 {removed_count} 条超过 {days_threshold} 天的记录")
    print(f"清理前总记录数：{total_before}，清理后总记录数：{total_after}")
    
    return cleaned_records

async def schedule_monitoring(login_user_name, interval_minutes=5, user_ids_file="user_ids.json", cookie_path="cookies.json"):
    """
    定时异步监控函数
    
    参数:
        interval_minutes: 监控间隔时间（分钟）
        user_ids_file: 用户ID列表文件路径
        cookie_path: cookies.json文件路径
    
    功能:
        每5分钟执行一次爬虫任务，并将结果保存到带有时间戳的文件中
    """
    with open(cookie_path, "r") as file:
        cookies = json.load(file)

    login_user_id = "Unknown_ID"
    for i in cookies:
        if i.get("user_name") == login_user_name:
            login_user_id = i.get("user_id")
            break
        
    interval_seconds = int(interval_minutes * 60)
    
    # 加载已存在的记录
    existing_records = []
    try:
        with open("user_records.json", "r", encoding="utf-8") as file:
            existing_records = json.load(file)
        print(f"已加载 {len(existing_records)} 条已有用户记录")
    except (FileNotFoundError, json.JSONDecodeError):
        print("未找到已有记录文件，将创建新文件")
        existing_records = []
    
    cleanup_counter = 6
    cleanup_interval = 6  # 每6次监控执行一次清理（大约每30分钟一次）
    while True:
        try:
            # 记录开始时间
            start_time = datetime.now()
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            print(f"\n{'='*60}")
            print(f"开始执行定时监控任务，时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            # 读取用户ID列表
            with open(user_ids_file, "r") as file:
                user_ids_list = json.load(file)
            user_ids = user_ids_list.get(login_user_id)
            print(user_ids)
            print(f"本次监控用户数量：{len(user_ids)}")
            
            # 执行爬虫任务，可以指定每个用户爬取的页数和停止条件
            max_pages_per_user = 5  # 可以调整这个值
            days_threshold = 60  # 60天阈值
            existing_records_path = "user_records.json"  # 已存在记录文件
            
            new_user_record_list = await run_spider(
                login_user_id,
                user_ids, 
                cookie_path, 
                max_pages_per_user,
                existing_records_path,
                days_threshold
            )
            
            # 合并新旧记录
            merged_records = merge_records(existing_records, new_user_record_list)
            # 每6次监控执行一次清理（大约每30分钟一次）
            cleanup_counter += 1
            if cleanup_counter >= cleanup_interval:
                print(f"\n执行定期清理：删除超过 {days_threshold} 天的旧记录")
                cleaned_records = clean_old_records(merged_records, days_threshold)
                merged_records = cleaned_records
                cleanup_counter = 0  # 重置计数器
            
            # 保存结果到文件（带有时间戳）
            # backup_file = f"user_records_{timestamp}.json"
            # with open(backup_file, "w", encoding="utf-8") as file:
            #     json.dump(merged_records, file, ensure_ascii=False, indent=2)
            
            # 更新主记录文件
            with open("user_records.json", "w", encoding="utf-8") as file:
                json.dump(merged_records, file, ensure_ascii=False, indent=2)
            
            # 更新existing_records，以便下次使用
            existing_records = merged_records
            
            # 计算执行时间
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            print(f"本次监控任务完成，耗时：{execution_time:.2f}秒")
            # print(f"备份文件已保存到：{backup_file}")
            print(f"主记录文件已更新：user_records.json")
            print(f"总用户记录数：{len(merged_records)}")
            
            # 统计新爬取的记录数
            new_records_count = sum(len(user["records"]) for user in new_user_record_list)
            total_records_count = sum(len(user["records"]) for user in merged_records)
            print(f"本次新爬取记录数：{new_records_count}")
            print(f"总记录数：{total_records_count}")
            
            # 显示下一次执行时间
            next_time = end_time.timestamp() + interval_seconds
            next_time_str = datetime.fromtimestamp(next_time).strftime("%Y-%m-%d %H:%M:%S")
            print(f"下一次监控将在 {interval_minutes} 分钟后执行，预计时间：{next_time_str}")
            print(f"{'='*60}\n")
            
            # 等待指定的时间间隔
            await asyncio.sleep(interval_seconds)
            
        except Exception as e:
            print(f"监控任务执行出错：{e}")
            import traceback
            traceback.print_exc()
            print(f"将在1分钟后重试...")
            await asyncio.sleep(60)  # 出错时等待1分钟再重试

# async def single_run(user_ids_file="user_ids.json", cookie_path="cookies.json", max_pages_per_user=5):
#     """
#     单次执行爬虫任务（保留原有功能）
    
#     参数:
#         user_ids_file: 用户ID列表文件路径
#         cookie_path: cookies.json文件路径
#         max_pages_per_user: 每个用户最大爬取页数
#     """
#     # 读取用户ID列表
#     with open(user_ids_file, "r") as file:
#         user_ids = json.load(file)
    
#     print(f"开始单次爬虫任务，用户数量：{len(user_ids)}，每用户最多爬取 {max_pages_per_user} 页")
    
#     # 执行爬虫任务
#     user_record_list = await run_spider(user_ids, cookie_path, max_pages_per_user)
    
#     # 保存结果到文件
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     output_file = f"user_records_single_{timestamp}.json"
#     with open(output_file, "w", encoding="utf-8") as file:
#         json.dump(user_record_list, file, ensure_ascii=False, indent=2)
    
#     print(f"单次爬虫任务完成，结果已保存到 {output_file}")

if __name__ == "__main__":
    interval_minutes = 5
    try:
        asyncio.run(schedule_monitoring("shuaiqbr", interval_minutes))
    except KeyboardInterrupt:
        print("\n监控已手动停止")