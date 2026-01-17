import asyncio
import json
import time
import os
from datetime import datetime, timedelta
from playwright.async_api import async_playwright,expect

async def create_browser_context(headless=True):
    # 启动Playwright和浏览器
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    
    # 创建上下文并添加cookies
    context = await browser.new_context()
    return p, browser, context

async def visit_problem_list(context, spider_page):
    should_stop = False
    problem_dict = {}
    page = await context.new_page()
    url = f"https://www.luogu.com.cn/problem/list?type=luogu&page={spider_page}"
    await page.goto(url)

    # 等待页面加载完成的断言
    await expect(page).to_have_url(url)
    
    # 等待主要内容区域加载完成
    main_content_locator = page.locator("#app > div.main-container.lside-nav > main > div > div > div > div.l-card.main")
    await expect(main_content_locator).to_be_visible()
    await expect(main_content_locator).not_to_be_empty()
    
    # 等待问题列表加载完成
    problem_list_locator = page.locator("div.list-wrap.table.border.overflow > div.row-wrap")
    await expect(problem_list_locator).to_be_visible()
    await expect(problem_list_locator).not_to_be_empty()

    print(f"已访问 问题 第 {spider_page} 页")
    page.wait_for_timeout(1000)

    for i in range(1, 51):
        # print("sgsdggf")
        # 尝试定位第i条记录
        problem_locator = page.locator(f"#app > div.main-container.lside-nav > main > div > div > div > div.l-card.main > div > div.list-wrap.table.border.overflow > div.row-wrap > div:nth-child({i}) > div:nth-child(2)")
        difficulty_locator = page.locator(f"#app > div.main-container.lside-nav > main > div > div > div > div.l-card.main > div > div.list-wrap.table.border.overflow > div.row-wrap > div:nth-child({i}) > div.difficulty > span > span")
        
        # 增加expect断言
        try:
            await expect(problem_locator).to_be_visible()
            await expect(difficulty_locator).to_be_visible()
        except:
            should_stop = True
            break

        # 增加expect断言
        is_ture = False
        while not is_ture:
            try:        
                problem = await problem_locator.text_content()
                difficulty = await difficulty_locator.text_content()
                await expect(problem_locator).not_to_be_empty()
                await expect(difficulty_locator).not_to_be_empty()
                is_ture = True
            except:
                pass
        
        print(problem, difficulty)
        problem_dict.update({problem: difficulty})
    
    print(problem_dict)
    await page.close()
    return [should_stop, problem_dict]

async def get_problem():
    p, browser, context = await create_browser_context(headless=False)

    if os.path.exists("problem_list.json"):
        with open("problem_list.json", "r", encoding="utf-8") as file:
            all_problem_dict = json.load(file)
    else:
        all_problem_dict = {}

    for i in range(len(all_problem_dict)//50 +1, 1000, 10):
        # 获取当前批次的用户ID
        print(f"正在爬取第 {i//10 + 1} 批问题，从 第 {i}到{i + 9} 页 共 10 个页面")
            
        # 2. 创建任务列表（当前批次）
        tasks = []
        for j in range(i, i+10):
            # 为每个用户创建异步任务，传递停止条件参数
            task = asyncio.create_task(
                visit_problem_list(
                    context, 
                    j, 
                )
            )
            tasks.append(task)
            
        # 3. 并行执行当前批次的所有任务
        batch_results = await asyncio.gather(*tasks)
        # all_problem_dict.update(batch_results[1])
        should_stop = False
        for j in batch_results:
            all_problem_dict.update(j[1])
            should_stop |= j[0]
            
        print(f"第 {i//10 + 1} 批题目爬取完成")
        if should_stop == True:
            break
        # 如果不是最后一批，等待一下再开始下一批
        await asyncio.sleep(0.5)  # 批次间等待0.5秒

    print(f"爬取结束！共 {len(all_problem_dict)} 道题目")
    with open("problem_list.json", "w", encoding="utf-8") as file:
        json.dump(all_problem_dict, file, ensure_ascii=False, indent=2)
    await context.close()
    await browser.close()
    await p.stop()

if __name__ == "__main__":
    asyncio.run(get_problem())

# #app > div.main-container.lside-nav > main > div > div > div > div.l-card.main > div > div.list-wrap.table.border.overflow > div.row-wrap > div:nth-child(1)
# //*[@id="app"]/div[4]/main/div/div/div/div[2]/div/div[1]/div[2]/div[50]
# //*[@id="app"]/div[4]/main/div/div/div/div[2]/div/div[1]/div[2]/div[50]
# #app > div.main-container.lside-nav > main > div > div > div > div.l-card.main > div > div.list-wrap.table.border.overflow > div.row-wrap > div:nth-child(1)
# #app > div.main-container.lside-nav > main > div > div > div > div.l-card.main > div > div.list-wrap.table.border.overflow > div.row-wrap > div:nth-child(1) > div:nth-child(2)
# #app > div.main-container.lside-nav > main > div > div > div > div.l-card.main > div > div.list-wrap.table.border.overflow > div.row-wrap > div:nth-child(1) > div.difficulty > span > span

# #app > div.main-container.lside-nav > main > div > div > div > div.l-card.main > div > div.list-wrap.table.border.overflow > div.row-wrap > div:nth-child(49) > div:nth-child(2)