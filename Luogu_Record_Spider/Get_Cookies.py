import cv2
import ddddocr
from datetime import datetime, timedelta
import json
import os
import asyncio
from playwright.async_api import Playwright, async_playwright

def Timeout_Detection(user_information): #上次登录是否超过40天
    user_name = user_information.get("user_name")
    str_date = user_information.get("earliest_date")
    last_date = datetime.strptime(str_date, "%Y-%m-%d").date()
    current_date = datetime.now().date()
    days_passed = (current_date - last_date).days
    if days_passed > 40:
        print(f"用户 {user_name} 最早登录时间已超过40天，需要重新登录")
    else:
        print(f"用户 {user_name} 最早登录时间未超过40天，无需重新登录")
    return days_passed > 40

def Recent_Login():
    with open("cookies.json", "r") as file:
        cookies = json.load(file)
    if len(cookies) == 0:
        return "Not_Found_User"
    recent_date = 100000
    user_information = cookies[0]
    for i in range(len(cookies)):
        pass_date = (datetime.now().date() - datetime.strptime(cookies[i].get("recent_date"), "%Y-%m-%d").date()).days
        if pass_date <= recent_date:
            recent_date = pass_date
            user_information = cookies[i]
    if Timeout_Detection(user_information):
        return "Not_Found_User"
    else:
        return user_information.get("user_name")


def Recognize_Auth_Code(image_path="auth_code.png"): #ocr识别验证码
    ocr = ddddocr.DdddOcr()
    with open(image_path, 'rb') as file:
        img_bytes = file.read()
    result = ocr.classification(img_bytes)
    print(result)
    return result
    
async def Get_New_Cookies(user_name, password): 
    # 使用上下文管理器启动异步 Playwright，避免全局变量导致的线程冲突
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://www.luogu.com.cn/auth/login")

        # 填用户信息 (全部加 await)
        await page.locator("#app > div.main-wrapper.lfe-body > div > div > div > div.step-1.active > div:nth-child(1) > div.input-group > input[type=text]").fill(user_name) 
        await page.locator("#app > div.main-wrapper.lfe-body > div > div > div > div.step-1.active > div:nth-child(1) > button").click()
        await page.locator("#app > div.main-wrapper.lfe-body > div > div > div > div.step-2.active > div.methods > div > input[type=password]").fill(password)

        # 填验证码
        success_login = False
        try_number = 0

        while not success_login:
            try_number += 1
            print(f"第 {try_number} 次尝试登录！")

            # 截图需要 await
            await page.locator("#app > div.main-wrapper.lfe-body > div > div > div > div.step-2.active > div.methods > div > div > div > img").screenshot(path="auth_code.png")
            
            auth_code = Recognize_Auth_Code() 

            await page.locator("#app > div.main-wrapper.lfe-body > div > div > div > div.step-2.active > div.methods > div > div > input").fill(auth_code)
            await page.locator("#app > div.main-wrapper.lfe-body > div > div > div > div.step-2.active > div.methods > div > button").click()

            try:
                # 等待 URL 跳转
                await page.wait_for_url(lambda url: "luogu.com.cn" in url and "/auth/login" not in url, timeout=7000)
                success_login = True
            except:
                if try_number == 3:
                    print(f"已有三次登录失败，请检查：您的用户名是否为 {user_name} ？您的密码是否为 {password} ？ 请您重新登录")
                    break
                success_login = False
            
            print(success_login)

            if success_login:
                # 获取 cookies 需要 await
                cookies = await context.cookies()
                print("登录成功！cookies为：", cookies)
                user_id = cookies[2].get("value")
                cookies_dist = {"user_name": user_name, "user_id": user_id, "earliest_date": datetime.now().strftime("%Y-%m-%d"), "recent_date": datetime.now().strftime("%Y-%m-%d"), "cookies": cookies}
                
                # 文件读写保持同步逻辑（在本地客户端应用中通常是可以接受的）
                if os.path.exists("cookies.json"):
                    with open("cookies.json", "r", encoding="utf-8") as file:
                        try:
                            old_cookies_dist = json.load(file)
                        except json.JSONDecodeError:
                            old_cookies_dist = []
                else:
                    old_cookies_dist = []
                
                found = False
                for i in range(len(old_cookies_dist)):
                    if old_cookies_dist[i].get("user_id") == user_id:
                        old_cookies_dist[i] = cookies_dist
                        found = True
                        break
            
                if not found:
                    old_cookies_dist.append(cookies_dist)

                with open("cookies.json", "w", encoding="utf-8") as file:
                    json.dump(old_cookies_dist, file, ensure_ascii=False, indent=2)
            else:
                print("登录失败！尝试重新登录")
                
                # 点击弹窗和刷新验证码
                await page.locator("body > div.swal2-container.swal2-center.swal2-backdrop-show > div > div.swal2-actions > button.swal2-confirm.swal2-styled.swal2-default-outline").click()
                await page.locator("#app > div.main-wrapper.lfe-body > div > div > div > div.step-2.active > div.methods > div > div > div > img").click()
                await page.wait_for_timeout(300)

        await page.close()
        await context.close()
        await browser.close()
        
        return success_login
    
if __name__ == "__main__":        

    user_name =  Recent_Login()
    if user_name == "Not_Found_User":
        success_login = False
        while not success_login:
            user_name = input("请输入用户名：")
            password = input("请输入用户密码：")
            success_login = asyncio.run(Get_New_Cookies(user_name, password))
            
    else:
        print(f"登录用户 {user_name}")