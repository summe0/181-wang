"""
全自动安全打卡脚本

依赖：
    python -m pip install playwright
    python -m playwright install chromium

建议使用环境变量保存账号密码：
    $env:CHECKIN_USERNAME = "你的账号"
    $env:CHECKIN_PASSWORD = "你的密码"
"""

import os
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# 密码和 Bark 地址只从环境变量读取；上传 GitHub 前不会把敏感信息写入代码。
PASSWORD = os.getenv("CHECKIN_PASSWORD", "").strip()
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK", "").strip()

CHECK_URLS = [
    (
        "https://njyj-social.njyjgl.cn/spp_grid_social/index.html"
        "#/loginQuestion?entId=a2303379-6843-4ec4-8591-2cc0aad43614"
        "&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82"
        "%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93"
        "%E9%AB%98%E6%A1%A5%E7%A4%BE%E5%8C%BA%E7%A5%9E%E8%B7%AF%E5%8F%A3%E6%9D%91319%E5%8F%B7"
        "&unitName=%E5%8D%97%E4%BA%AC%E5%A4%A7%E5%9C%A3%E5%B0%8F%E4%BE%A0%E9%A4%90%E9%A5%AE%E7%AE%A1%E7%90%86%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"
        "&checkId=41ad980d-307d-4feb-b40e-3d3e2f559662&clientType=&type=2"
    )
]

# 41 家单位：每条记录使用该单位自己的登录手机号。
# 如号码实际不同，只需修改对应这一行的 username。
CHECKINS = [
   # {"name":"程秀早餐店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=2b808d4e-fef9-4e39-bc01-be7ba44261b9&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E7%A8%8B%E7%A7%80%E6%97%A9%E9%A4%90%E5%BA%97&checkId=38fb7ad4-dd5b-4ec0-91be-1e55dcf9814d&clientType=&type=2","username":"19259642542"},
    {"name":"宁琳电池","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=d2b22098-b5d1-4ce1-a3f1-aaf94912aa0c&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B730%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%AE%81%E7%8E%B2%E7%94%B5%E6%B1%A0%E9%94%80%E5%94%AE%E5%BA%97&checkId=4ebcd253-25ce-4761-af1f-ea245d88618e&clientType=&type=2","username":"19393322148"},
  #  {"name":"南京市江宁区登科市井川菜馆","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=6706f228-c69f-4672-8718-040f3733a7df&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E7%99%BB%E7%A7%91%E5%B8%82%E4%BA%95%E5%B7%9D%E8%8F%9C%E9%A6%86&checkId=a45e3c36-dce1-49d7-931d-e66ab7944078&clientType=&type=2","username":"17825781030"},
  #  {"name":"南京市江宁区卢浚熙餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=838c7290-b014-4ec8-8592-edfa72495080&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%8D%A2%E6%B5%9A%E7%86%99%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=d4dce0e4-6944-4370-a372-80bb9335c168&clientType=&type=2","username":"18377044476"},
  #  {"name":"江宁区蓼茸餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=a2cab729-a5db-4f4d-8dc5-bb752f0349d3&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E8%93%BC%E8%8C%B8%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=1b2232d5-453c-479b-9cd9-bcc9e6f2ee71&clientType=&type=2","username":"14724564423"},
  #  {"name":"江宁区冯香酸菜鱼店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=3a498ba1-1179-42e9-80a6-74ae13aac87b&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%86%AF%E9%A6%99%E9%85%B8%E8%8F%9C%E9%B1%BC%E5%BA%97&checkId=cf13af31-27ea-40a3-9fb6-4ee226605937&clientType=&type=2","username":"19022195451"},
  #  {"name":"江宁区饺来乐饺子馆","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=5274c4fb-7c40-46ef-a1bc-0190c794639c&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%A5%BA%E6%9D%A5%E4%B9%90%E9%A5%BA%E5%AD%90%E9%A6%86&checkId=55b4ee2e-f196-4b24-9449-1a852cada024&clientType=&type=2","username":"13943540838"},
  #  {"name":"江宁区鑫昌旺餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=66c3978d-0398-438a-a67e-b98a5afabbda&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%91%AB%E6%98%8C%E6%97%BA%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=55d60deb-1d4b-4fa7-9733-26065111dc4c&clientType=&type=2","username":"17181289134"},
   # {"name":"江宁区百鲁喜餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=937a748d-48d1-4dc2-bd90-0eb8002408d9&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E7%99%BE%E9%B2%81%E5%96%9C%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=bb84a6b2-7713-4ec7-bc78-587636ae18cb&clientType=&type=2","username":"17878206497"},
   # {"name":"江宁区福绣昌面馆","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=04216603-7025-45e2-a519-5d54d8089f33&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E7%A6%8F%E7%BB%A3%E6%98%8C%E9%9D%A2%E9%A6%86&checkId=2582fbc5-c62d-4c62-847d-60a3460d9e5e&clientType=&type=2","username":"17817944799"},
  #  {"name":"江宁区龚巍浩聚皮肚面","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=c5fbac9b-93e4-4d68-885e-0f8b15ab7869&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%BE%9A%E5%B7%8D%E6%B5%A9%E8%81%9A%E7%9A%AE%E8%82%9A%E9%9D%A2&checkId=f087121c-497f-4c18-820e-1b63ed49ace2&clientType=&type=2","username":"19264712368"},
  #  {"name":"江宁区西景园餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=797b31e8-1ab0-43c9-81b6-b58ed13ba896&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B730%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E8%A5%BF%E6%99%AF%E5%9B%AD%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=d454416e-2a1a-4fd3-bc3d-8b659959c843&clientType=&type=2","username":"14936757175"},
 #   {"name":"南京市江宁区乡村部落餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=b6fe259d-2ce9-4b53-ad5a-fc139632ece1&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%80%A1%E6%99%AF%E8%A1%978%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B9%A1%E6%9D%91%E9%83%A8%E8%90%BD%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=44a4729c-143c-4770-b96a-e766e9756b56&clientType=&type=2","username":"13476534457"},
#    {"name":"南京市江宁区乡村部落餐饮店2","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=6906b303-f567-4682-b467-0b6a33cb88ca&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%80%A1%E6%99%AF%E8%A1%978%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B9%A1%E6%9D%91%E9%83%A8%E8%90%BD%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=6ce35b96-1f8c-430e-9ee4-326f6ffcb482&clientType=&type=2","username":"19048075114"},
 #   {"name":"南京哈哈鱼庄餐饮有限公司","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=3bc0dc95-b3ca-4d1d-b642-49fe592ca168&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%80%A1%E6%99%AF%E8%A1%978%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%93%88%E5%93%88%E9%B1%BC%E5%BA%84%E9%A4%90%E9%A5%AE%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8&checkId=da49d191-6533-43f1-af19-8cc36a4981a4&clientType=&type=2","username":"19853462145"},
 #   {"name":"江宁区风雅颂餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=acb8c9c5-ffd0-46a2-ac29-1eaed020df58&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%A3%8E%E9%9B%85%E9%A2%82%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=1ea14b84-48b4-402d-8942-aace292e6446&clientType=&type=2","username":"15775366655"},
 #   {"name":"南京市江宁区香千家熟食店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=493bcb4c-affe-44ff-ab51-70b0c13cd4ca&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%A6%99%E5%8D%83%E5%AE%B6%E7%86%9F%E9%A3%9F%E5%BA%97&checkId=8ca91ec8-0fb6-4fd7-af44-b14f6b761e74&clientType=&type=2","username":"19635203901"},
#    {"name":"江宁区香鹏欣餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=c5704e50-ce57-4072-a2c8-852956f53217&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%A6%99%E9%B9%8F%E6%AC%A3%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=4c23dd30-18f1-4673-9764-cd923c45141f&clientType=&type=2","username":"13009240526"},
  #  {"name":"江宁区曹以龙餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=4ec38ab8-c3f2-45c2-b18f-f0921f6cc453&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%9B%B9%E4%BB%A5%E9%BE%99%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=58cbb8ac-32db-4b02-9e04-3c02f0a2ae60&clientType=&type=2","username":"19398546855"},
 #   {"name":"南京市江宁区佳明汤包馆","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=f0b2097c-80e6-41bc-a8b3-f06e3447b6e0&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%BD%B3%E6%98%8E%E6%B1%A4%E5%8C%85%E9%A6%86&checkId=b11c80ab-b79e-48fb-bf4e-e9f43d015de5&clientType=&type=2","username":"13984914859"},
 #   {"name":"南京市江宁区御置车餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=4641cc39-fd30-4d0e-8b20-3e64f092707a&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%BE%A1%E7%BD%AE%E8%BD%A6%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=fe3e9821-b524-466f-9e15-1b5dbabf8b6a&clientType=&type=2","username":"17839408904"},
   # {"name":"南京市江宁区荀之骁小吃店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=8e2c900c-57ea-46fb-929d-a4a5bfac2d21&unitAddress=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B7%E9%B8%BF%E4%BA%91%E5%9D%8A27%E5%B9%A2119%E5%AE%A4&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E8%8D%80%E4%B9%8B%E9%AA%81%E5%B0%8F%E5%90%83%E5%BA%97&checkId=0ef2f353-f235-486b-8728-924a15b71238&clientType=&type=2","username":"13079282080"},
 #   {"name":"江宁区赵馨彤大碗皮肚面馆","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=eeacfdc1-f064-4747-87e6-e3cbabfd3931&unitAddress=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B7%E9%B8%BF%E4%BA%91%E5%9D%8A27%E5%B9%A2120%E5%AE%A4&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E8%B5%B5%E9%A6%A8%E5%BD%A4%E5%A4%A7%E7%A2%97%E7%9A%AE%E8%82%9A%E9%9D%A2%E9%A6%86&checkId=7f2d75ff-0e9c-47d0-9510-9b2eee0cf90e&clientType=&type=2","username":"17072192709"},
#    {"name":"南京市江宁区川天下餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=07e04f51-d2a1-4ed3-9082-cadcba10f87f&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%B7%9D%E5%A4%A9%E4%B8%8B%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=1bfbdd84-9dd4-4314-9f51-807d91e8cc69&clientType=&type=2","username":"13076805274"},
#    {"name":"向三饭店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=94e7299e-6317-4d3c-8558-3cc394b69cb4&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E5%90%91%E4%B8%89%E9%A5%AD%E5%BA%97&checkId=2f508e74-a586-4f92-a558-f352878ae5d1&clientType=&type=2","username":"13381521345"},
#    {"name":"南京市江宁区张洋土菜馆","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=0cb4e1fd-9fe7-4153-851c-bc9d7442a03a&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%BC%A0%E6%B4%8B%E5%9C%9F%E8%8F%9C%E9%A6%86&checkId=e5778e1e-d4b4-4962-8d47-fc213de79cb1&clientType=&type=2","username":"16626193816"},
#    {"name":"南京市江宁区波哥视频店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=bc7e2940-592c-4c42-9de5-3ef5c665c0d9&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%B3%A2%E5%93%A5%E8%A7%86%E9%A2%91%E5%BA%97&checkId=42b4afe1-ffa6-4abe-98d7-bd02980a014e&clientType=&type=2","username":"19909538124"},
#    {"name":"南京市江宁区俞老汉烧鸡公火锅店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=606aeaae-dcbc-4755-9447-bb612b6c57a5&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%BF%9E%E8%80%81%E6%B1%89%E7%83%A7%E9%B8%A1%E5%85%AC%E7%81%AB%E9%94%85%E5%BA%97&checkId=b2e4d8ca-0e36-427f-a626-81eba6257814&clientType=&type=2","username":"17323009522"},
#    {"name":"南京市江宁区吉炫电动自行车经营部","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=f800da69-3617-4c39-ad8f-5018b77aa460&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B729%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%90%89%E7%82%AB%E7%94%B5%E5%8A%A8%E8%87%AA%E8%A1%8C%E8%BD%A6%E7%BB%8F%E8%90%A5%E9%83%A8&checkId=85dfb0d1-1f0b-4e8a-b62e-86e2be6ce0db&clientType=&type=2","username":"19792391004"},
#    {"name":"南京市江宁区鸿云坊牛肉汤店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=ff469a52-b5c3-48e7-87d2-4293022536f8&unitAddress=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B7%E9%B8%BF%E4%BA%91%E5%9D%8A28%E5%B9%A2119%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%B8%BF%E4%BA%91%E5%9D%8A%E7%89%9B%E8%82%89%E6%B1%A4%E5%BA%97&checkId=d0fe5a77-2c59-4b73-a89c-510272a2dfc5&clientType=&type=2","username":"14747377943"},
 #   {"name":"南京市江宁区岩奇餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=ddd04812-5bb0-444a-9d4e-753cf5e4c352&unitAddress=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%9C%E5%B1%B1%E8%A1%97%E9%81%93%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B7%E9%B8%BF%E4%BA%91%E5%9D%8A30%E5%B9%A2113%E5%AE%A4&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%B2%A9%E5%A5%87%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=9678d600-7883-4b4a-8596-f127d829e498&clientType=&type=2","username":"19862155115"},
#    {"name":"南京市江宁区黄家馒头店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=7ee67a04-32d2-4cb2-ae60-8b60096c85ca&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%80%A1%E6%99%AF%E8%A1%978%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E9%BB%84%E5%AE%B6%E9%A6%92%E5%A4%B4%E5%BA%97&checkId=e4219d72-2ee9-42d9-a160-1144d6943aa7&clientType=&type=2","username":"13360573477"},
#    {"name":"江宁区大吴电动自行车销售中心","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=aedd8806-5a09-44cd-ac2c-58eedf00b139&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B730%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%A4%A7%E5%90%B4%E7%94%B5%E5%8A%A8%E8%87%AA%E8%A1%8C%E8%BD%A6%E9%94%80%E5%94%AE%E4%B8%AD%E5%BF%83&checkId=d1e819ce-a296-4a84-8022-08a9976cd287&clientType=&type=2","username":"18014414465"},
#    {"name":"江宁区大之秦面馆","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=f429f650-bd49-4d00-8bba-75f99cc65ef1&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%A4%A7%E4%B9%8B%E7%A7%A6%E9%9D%A2%E9%A6%86&checkId=165f28fc-4c83-4a17-b46c-b9ae63b06665&clientType=&type=2","username":"13328728530"},
#    {"name":"江宁区怡一乐餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=74ee5f21-4c98-4b5e-a098-afddf7f8d026&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%80%A1%E4%B8%80%E4%B9%90%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=57f65f07-259e-418a-87c6-ef7957f281f4&clientType=&type=2","username":"18158205497"},
#    {"name":"江宁区舒梅电动自行车经营部","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=dcac53f3-99a0-402e-a7e9-985549c24a78&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B730%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E8%88%92%E6%A2%85%E7%94%B5%E5%8A%A8%E8%87%AA%E8%A1%8C%E8%BD%A6%E7%BB%8F%E8%90%A5%E9%83%A8&checkId=0bd7679a-24c2-4200-9aa8-28b7d0351e1f&clientType=&type=2","username":"13840743232"},
#    {"name":"南京市江宁区何萱权餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=56004c1c-b9f4-44cd-88d3-6e4c3f6aab2e&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%BD%95%E8%90%B1%E6%9D%83%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=20b8965d-b78e-427b-8137-a418865c2991&clientType=&type=2","username":"14797806794"},
#    {"name":"南京韩厨家常菜馆","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=0b99b656-a4cc-48fd-ab84-6404328a1677&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E6%80%A1%E6%99%AF%E8%A1%978%E5%8F%B7&unitName=%E5%8D%97%E4%BA%AC%E9%9F%A9%E5%8E%A8%E5%AE%B6%E5%B8%B8%E8%8F%9C%E9%A6%86&checkId=d653a590-2cbf-458d-929f-9dd29b104170&clientType=&type=2","username":"19582292798"},
#    {"name":"江宁区前承苏雨餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=1e19f4fc-b58f-4e2e-a24b-73c6de65ebeb&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B730%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E5%89%8D%E6%89%BF%E8%8B%8F%E9%9B%A8%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=f3a3f780-0168-41e8-8769-6988e8d06d72&clientType=&type=2","username":"18663459438"},
#    {"name":"南京市江宁区纪为陵餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=1216643c-e242-40ad-b624-e7b4104d29a7&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B728%E5%B9%A2&unitName=%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E7%BA%AA%E4%B8%BA%E9%99%B5%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=93d2fe07-dc26-49a0-856d-6bf52920269b&clientType=&type=2","username":"13258841345"},
#    {"name":"江宁区辣婆家餐饮店","url":"https://njyj-social.njyjgl.cn/spp_grid_social/index.html#/loginQuestion?entId=b478475a-a2fe-4b19-94eb-b59a4e68bd11&unitAddress=%E6%B1%9F%E8%8B%8F%E5%8D%97%E4%BA%AC%E5%B8%82%E6%B1%9F%E5%AE%81%E5%8C%BA%E4%B8%B0%E6%B3%BD%E8%B7%AF118%E5%8F%B727%E5%B9%A2&unitName=%E6%B1%9F%E5%AE%81%E5%8C%BA%E8%BE%A3%E5%A9%86%E5%AE%B6%E9%A4%90%E9%A5%AE%E5%BA%97&checkId=1bd4a7e3-d590-45a3-9783-1b5de0db6030&clientType=&type=2","username":"19782808350"},
]

def save_screenshot(page, screenshot_path):
    # 默认关闭截图，避免长期运行占用磁盘空间。
    return


def send_wechat_notification(success_count, fail_count, failed_names):
    """发送运行汇总到企业微信群机器人。"""
    if not WECHAT_WEBHOOK:
        print("未配置 WECHAT_WEBHOOK，跳过企业微信推送。")
        return

    title = "远泰社区今日打卡结果"

    message = (
        f"{title}\n"
        f"今日共打卡 {len(CHECKINS)} 家\n"
        f"✅ 成功：{success_count} 家\n"
        f"❌ 失败：{fail_count} 家"
    )

    if failed_names:
        message += "\n失败店家：\n" + "\n".join(
            f"- {name}" for name in failed_names
        )
    else:
        message += "\n🎉 所有店家均打卡成功"

    payload = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            WECHAT_WEBHOOK,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "daily-checkin",
            },
            method="POST",
        )

        with urlopen(request, timeout=15) as response:
            result = response.read().decode("utf-8")

        if '"errcode":0' in result:
            print("企业微信推送已发送。")
        else:
            print(f"企业微信推送返回异常：{result}")

    except Exception as exc:
        print(f"企业微信推送失败：{exc}")


def page_has_text(page, *texts):
    # 提交后页面可能同时保留旧视图和新视图，导致存在多个 body。
    # all_inner_texts() 可以安全读取这些视图，避免 strict mode violation。
    body = "\n".join(page.locator("body").all_inner_texts()).lower()
    return any(text.lower() in body for text in texts)


def process_daily_check(page, url, username, screenshot_path):
    print("\n开始访问打卡页面...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # 登录页面可能稍晚渲染。该页面的账号框不一定是 type="text"，
        # 因此同时按 placeholder、密码框和普通输入框兼容查找。
        try:
            page.wait_for_timeout(1_500)
            username_candidates = [
                "input[placeholder*='手机号']",
                "input[placeholder*='账号']",
                "input[type='tel']",
                "input[type='text']",
                "input:not([type])",
            ]
            username_input = None
            for selector in username_candidates:
                candidate = page.locator(selector).first
                try:
                    if candidate.is_visible(timeout=1_000):
                        username_input = candidate
                        break
                except PlaywrightTimeoutError:
                    continue

            password_input = page.locator("input[type='password']").first
            if username_input is not None and password_input.is_visible(timeout=2_000):
                print("检测到登录页面，正在自动填写账号密码...")
                username_input.fill(username)
                password_input.fill(PASSWORD)

                login_button = page.locator(
                    ".login-button, button:has-text('登录'), "
                    "div:has-text('登录'), input[type='submit']"
                ).last
                login_button.click(timeout=10_000)
                print("已点击登录，等待页面加载...")
                page.wait_for_timeout(5_000)
        except PlaywrightTimeoutError:
            print("⚠️ 未找到可用的登录控件。")

        # 原脚本只判断 /question，但实际地址是 #/loginQuestion。
        # 这里同时判断 URL 和页面文字，避免大小写或路由名称导致误判。
        try:
            page.wait_for_function(
                """() => {
                    const hash = location.hash.toLowerCase();
                    const text = document.body.innerText || '';
                    const hasLoginForm = !!document.querySelector(
                        'input[type="password"]'
                    ) && text.includes('登录');
                    return (!hasLoginForm && (
                    hash.includes('loginquestion') ||
                    hash.includes('/question') ||
                     text.includes('今日已打卡') ||
                    text.includes('打卡成功') ||
                    text.includes('该用户对此场所') ||
                    text.includes('已经打卡')
                ));
                }""",
                timeout=30_000,
            )
        except PlaywrightTimeoutError:
            print("⚠️ 未能确认已进入题目页。")
            print(f"当前地址: {page.url}")
            save_screenshot(page, screenshot_path)
            return False

        print(f"当前地址: {page.url}")

        if page_has_text(
            page,
            "今日已打卡",
            "打卡成功",
            "该用户对此场所，今日已打卡",
            "该用户对此场所今日已打卡",
            "已经打卡",
            "今日已经完成",
        ):
            print("✅ 该单位今日已完成打卡，跳过。")
            save_screenshot(page, screenshot_path)
            return True

        if "loginquestion" not in page.url.lower() and "question" not in page.url.lower():
            print("⚠️ 当前页面不是题目页，也没有检测到已打卡提示。")
            save_screenshot(page, screenshot_path)
            return False

        print("已进入题目页面，开始自动勾选...")
        page.wait_for_timeout(5_000)

        yes_options = page.get_by_text("是", exact=True)
        no_options = page.get_by_text("否", exact=True)
        yes_count = yes_options.count()
        no_count = no_options.count()
        print(f"找到 {yes_count} 个“是”选项，{no_count} 个“否”选项")

        if yes_count < 3 or no_count < 6:
            print(f"⚠️ 选项数量异常：是={yes_count}，否={no_count}")
            page_text = "\n".join(page.locator("body").all_inner_texts())
            print("页面文字预览:", page_text[:500])
            save_screenshot(page, screenshot_path)
            return False

        for index in range(3):
            yes_options.nth(index).click()
            page.wait_for_timeout(300)
            print(f"✅ 第 {index + 1} 题已选择“是”")

        # “否”选项集合中前 3 个仍然对应第 1-3 题，
        # 第 4-6 题必须从下标 3 开始，否则会把前 3 题再次改成“否”。
        for index in range(3, 6):
            no_options.nth(index).click()
            page.wait_for_timeout(300)
            print(f"✅ 第 {index + 1} 题已选择“否”")

        submit_selectors = [
            "button:has-text('提交')",
            "button:has-text('确认')",
            "button:has-text('完成')",
            ".submit-btn",
            ".submit-button",
            "input[type='submit']",
        ]

        submit_button = None
        for selector in submit_selectors:
            candidate = page.locator(selector).last
            try:
                if candidate.is_visible(timeout=2_000):
                    submit_button = candidate
                    print(f"找到提交按钮: {selector}")
                    break
            except PlaywrightTimeoutError:
                continue

        if submit_button is None:
            print("⚠️ 未找到提交按钮。")
            save_screenshot(page, screenshot_path)
            return False

        submit_button.click()
        print("已点击提交按钮，等待结果...")

        # 提交后的页面可能是提示框、详情页、历史记录页或路由跳转。
        # 轮询这些状态，避免只依赖某一个固定中文提示。
        success = False
        for _ in range(10):
            page.wait_for_timeout(1_000)
            current_url = page.url.lower()
            success_text = page_has_text(
                page,
                "成功",
                "提交成功",
                "操作成功",
                "已打卡",
                "今日已打卡",
                "打卡时间",
                "打卡详情",
                "历史记录",
                "该用户对此场所，今日已打卡",
                "该用户对此场所今日已打卡",
            )
            route_changed = any(
                keyword in current_url
                for keyword in ("history", "detail", "result", "success")
            )
            try:
                submit_disappeared = not submit_button.is_visible(timeout=500)
            except Exception:
                submit_disappeared = True

            if success_text or route_changed or submit_disappeared:
                success = True
                break

        if success:
            print("🎉 打卡成功。")
            save_screenshot(page, screenshot_path)
            return True

        print("⚠️ 已点击提交，但未确认成功。")
        save_screenshot(page, screenshot_path)
        return False

    except Exception as exc:
        print(f"❌ 处理失败: {exc}")
        save_screenshot(page, screenshot_path)
        return False


def main():
    if not PASSWORD:
        print("未设置 CHECKIN_PASSWORD，无法登录。", file=sys.stderr)
        return 1

    output_dir = Path(__file__).parent
    success_count = 0
    fail_count = 0
    failed_names = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.set_default_timeout(15_000)

        try:
            for index, checkin in enumerate(CHECKINS):
                print("\n" + "=" * 50)
                print(f"处理第 {index + 1}/{len(CHECKINS)} 家：{checkin['name']}")
                print("=" * 50)

                screenshot = output_dir / (
                    f"daily_check_result_{index}_{date.today():%Y-%m-%d}.png"
                )

                if process_daily_check(
                    page, checkin["url"], checkin["username"], screenshot
                ):
                    success_count += 1
                else:
                    fail_count += 1
                    failed_names.append(checkin["name"])

                if index < len(CHECKINS) - 1:
                    print("等待 5 秒后处理下一家...")
                    page.wait_for_timeout(5_000)

        finally:
            browser.close()

        print("\n" + "=" * 50)
    print(f"打卡完成！成功: {success_count}, 失败: {fail_count}")
    print("失败清单：", failed_names)
    print("=" * 50)
    send_wechat_notification(success_count, fail_count, failed_names)
    # 无论有没有失败，脚本本身标记运行成功，消除红色报错
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
