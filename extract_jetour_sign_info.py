#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import yaml
from datetime import datetime


def load_config():
    """加载配置文件"""
    with open('jetour_configuration.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_current_month():
    """获取当前月份，格式：YYYYMM"""
    return datetime.now().strftime('%Y%m')


def make_request(config, command_name, custom_params=None):
    """执行HTTP请求"""
    command = config['rest_command'][command_name]
    url = command['url']
    method = command['method']
    params = command['params'].copy()
    headers = command['headers'].copy()

    # 替换动态参数
    for key, value in params.items():
        if isinstance(value, str):
            # 处理双引号包围的模板字符串
            if '{{ now().strftime("%Y%m") }}' in value:
                params[key] = value.replace('{{ now().strftime("%Y%m") }}', get_current_month())
            # 处理单引号包围的模板字符串
            elif "{{ now().strftime('%Y%m') }}" in value:
                params[key] = value.replace("{{ now().strftime('%Y%m') }}", get_current_month())

    # 从环境变量获取敏感信息
    access_token = os.environ.get('ACCESS_TOKEN')
    task_id = os.environ.get('TASK_ID')

    if access_token:
        for key, value in params.items():
            if isinstance(value, str) and 'access_token' in value:
                params[key] = access_token
    if task_id:
        for key, value in params.items():
            if isinstance(value, str) and 'taskId' in value:
                params[key] = task_id

    # 添加自定义参数
    if custom_params:
        params.update(custom_params)

    print(f"执行请求: {method} {url}")
    print(f"参数: {params}")

    response = requests.request(method, url, params=params, headers=headers, verify=command['verify_ssl'], timeout=command['timeout'])
    response.raise_for_status()
    return response.json()


def calculate_sign_stats(sign_record):
    """计算签到统计信息"""
    total_days = len(sign_record)
    signed_days = sign_record.count('1') + sign_record.count('2')
    makeup_days = sign_record.count('2')
    missed_days = sign_record.count('0')
    sign_rate = (signed_days / total_days) * 100 if total_days > 0 else 0

    return {
        'totalDays': total_days,
        'signedDays': signed_days,
        'makeupDays': makeup_days,
        'missedDays': missed_days,
        'signRate': round(sign_rate, 1)
    }


def main():
    """主函数"""
    try:
        # 加载配置
        config = load_config()

        # 1. 获取任务信息
        task_info = make_request(config, 'jetour_task_load')
        print("任务信息获取成功")

        # 2. 获取签到记录
        sign_record_data = make_request(config, 'jetour_sign_record')
        sign_record = sign_record_data.get('signRecord', '')
        print("签到记录获取成功")

        # 3. 获取签到页面信息（包含奖励信息）
        sign_page_data = make_request(config, 'jetour_sign_page')
        print("签到页面信息获取成功")

        # 4. 计算签到统计信息
        sign_stats = calculate_sign_stats(sign_record)
        print("签到统计计算成功")

        # 5. 整合所有数据
        combined_data = {
            'timestamp': datetime.now().isoformat(),
            'taskInfo': task_info.get('data', {}).get('taskInfo', {}),
            'signRecord': sign_record_data.get('signRecord', ''),
            'signStats': sign_stats,
            'rewardInfo': sign_page_data.get('rewardInfo', {})
        }

        # 6. 保存到sign-data.json文件
        with open('sign-data.json', 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        print("数据保存成功")

        print("\n签到信息提取完成！")
        print(f"签到记录: {sign_record}")
        print(f"签到统计: {sign_stats}")

    except Exception as e:
        print(f"提取失败: {str(e)}")
        raise


if __name__ == '__main__':
    main()
