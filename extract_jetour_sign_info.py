import requests
from datetime import datetime

# 捷途签到API信息提取脚本
# 用于从API响应中提取关键签到信息和奖励数据

class JetourSignInfoExtractor:
    def __init__(self, access_token, task_id):
        self.access_token = access_token
        self.task_id = task_id
        self.base_url = "https://mobile-consumer.jetour.com.cn/web/task"
        self.headers = {
            "Host": "mobile-consumer.jetour.com.cn",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh",
            "Content-Type": "application/json",
            "Origin": "https://h5-app.jetour.com.cn",
            "Referer": "https://h5-app.jetour.com.cn/",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ios/1.0.0"
        }
    
    def get_sign_record(self, month=None):
        """获取签到记录"""
        url = f"{self.base_url}/sign/sign-record"
        params = {
            "access_token": self.access_token,
            "taskId": self.task_id,
            "monthInYear": month or datetime.now().strftime("%Y%m")
        }
        
        response = requests.get(url, params=params, headers=self.headers, verify=True, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_sign_page(self):
        """获取签到页面信息"""
        url = f"{self.base_url}/sign/sign-page"
        params = {
            "access_token": self.access_token,
            "taskId": self.task_id
        }
        
        response = requests.get(url, params=params, headers=self.headers, verify=True, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_task_info(self):
        """获取任务信息"""
        url = f"{self.base_url}/tasks/load-one"
        params = {
            "sceneCode": "signInScene",
            "terminal": "4",
            "access_token": self.access_token
        }
        
        response = requests.get(url, params=params, headers=self.headers, verify=True, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def extract_key_info(self):
        """提取关键签到信息"""
        print("=" * 60)
        print("捷途签到信息提取结果")
        print("=" * 60)
        
        # 存储所有提取的数据
        extracted_data = {
            "timestamp": datetime.now().isoformat(),
            "taskInfo": {},
            "signRecord": "",
            "signStats": {},
            "rewardInfo": {}
        }
        
        # 1. 获取任务基本信息
        try:
            task_data = self.get_task_info()
            task_info = task_data.get("data", {}).get("taskInfo", {})
            extracted_data["taskInfo"] = task_info
            
            print(f"\n【任务基本信息】")
            print(f"任务名称: {task_info.get('name', '未知')}")
            print(f"任务ID: {task_info.get('id', '未知')}")
            print(f"参与人数: {task_info.get('joinCount', '未知')}人")
            
            # 提取签到规则
            rule_desc = task_info.get('taskRuleDesc', '')
            if rule_desc:
                print(f"\n【签到规则】")
                # 简单处理HTML标签
                rule_desc = rule_desc.replace('<p>', '').replace('</p>', '\n')
                rule_desc = rule_desc.replace('<span style="font-size: 16px;">', '').replace('</span>', '')
                print(rule_desc.strip())
        except Exception as e:
            print(f"获取任务信息失败: {e}")
        
        # 2. 获取签到记录
        try:
            record_data = self.get_sign_record()
            sign_data = record_data.get("data", {})
            
            print(f"\n【签到记录】")
            print(f"查询月份: {sign_data.get('month', '未知')}")
            print(f"当月天数: {sign_data.get('monthDays', '未知')}")
            
            sign_record = sign_data.get('signRecord', '')
            extracted_data["signRecord"] = sign_record
            
            if sign_record:
                # 计算签到统计
                total_days = len(sign_record)
                signed_days = sign_record.count('1')  # 正常签到
                make_up_days = sign_record.count('2')  # 补签
                missed_days = total_days - signed_days - make_up_days  # 未签到
                sign_rate = ((signed_days + make_up_days) / total_days * 100) if total_days > 0 else 0
                
                # 保存签到统计
                extracted_data["signStats"] = {
                    "totalDays": total_days,
                    "signedDays": signed_days,
                    "makeupDays": make_up_days,
                    "missedDays": missed_days,
                    "signRate": round(sign_rate, 1)
                }
                
                print(f"签到天数: {signed_days}天")
                print(f"补签天数: {make_up_days}天")
                print(f"未签天数: {missed_days}天")
                print(f"签到率: {sign_rate:.1f}%")
                print(f"签到记录: {sign_record}")
                print(f"记录说明: 1=正常签到, 2=补签, 0/n=未签到")
        except Exception as e:
            print(f"获取签到记录失败: {e}")
        
        # 3. 获取签到奖励信息
        try:
            page_data = self.get_sign_page()
            page_info = page_data.get("data", {})
            
            # 保存奖励信息，处理None值
            point_reward = page_info.get("pointReward") or 0
            member_reward = page_info.get("memberReward") or 0
            
            extracted_data["rewardInfo"] = {
                "pointReward": point_reward,
                "memberReward": member_reward,
                "cycleType": page_info.get("cycleType", 0),
                "continuousDays": page_info.get("cycleDays", 0),
                "nextStageReward": page_info.get("nextStageReward", {})
            }
            
            print(f"\n【奖励信息】")
            print(f"单次签到积分: {point_reward}捷途币")
            print(f"单次签到会员积分: {member_reward}旅行值")
            print(f"签到周期类型: {'连续签到' if page_info.get('cycleType') == 2 else '其他'}")
            print(f"当前连续天数: {page_info.get('cycleDays', '未知')}天")
            
            # 下一阶段奖励
            next_reward = page_info.get('nextStageReward', {})
            if next_reward:
                print(f"\n【下一阶段奖励】")
                print(f"需要连续签到: {next_reward.get('needContinuousDays', '未知')}天")
                print(f"可获得积分: {next_reward.get('pointReward', '未知')}捷途币")
                print(f"可获得会员积分: {next_reward.get('memberReward', '未知')}旅行值")
        except Exception as e:
            print(f"获取奖励信息失败: {e}")
        
        # 4. 生成JSON数据文件
        import json
        try:
            with open('sign-data.json', 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, ensure_ascii=False, indent=2)
            print(f"\n【数据保存】")
            print(f"签到数据已保存到 sign-data.json")
        except Exception as e:
            print(f"保存数据失败: {e}")
        
        print(f"\n{"=" * 60}")
        print("信息提取完成")
        print("=" * 60)

import os

# 使用示例
if __name__ == "__main__":
    # 从环境变量获取配置参数，支持GitHub Secrets
    ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN', 'jTAd44hVSuVUFBe5iAIAaQAAAAAAAAAE')
    TASK_ID = os.environ.get('TASK_ID', '3439799346990943525')
    
    # 验证必填参数
    if not ACCESS_TOKEN:
        print("错误: 未提供ACCESS_TOKEN")
        exit(1)
    if not TASK_ID:
        print("错误: 未提供TASK_ID")
        exit(1)
    
    print(f"使用ACCESS_TOKEN: {ACCESS_TOKEN[:10]}...")
    print(f"使用TASK_ID: {TASK_ID}")
    
    # 创建提取器并运行
    extractor = JetourSignInfoExtractor(ACCESS_TOKEN, TASK_ID)
    extractor.extract_key_info()
