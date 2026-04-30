#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from http import HTTPStatus
from dashscope import Application
from promot.promot_jiaoyuan import promot_j
load_dotenv()
promot = promot_j
# api_key=os.getenv("ALIYUN_API_KEY")
# print(api_key)
# app_id = os.getenv("ALIYUN_APP_ID_J")
#
# print(app_id)
def call_with_session():
    response = Application.call(
        # 若没有配置环境变量，可用百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
        api_key=os.getenv("ALIYUN_API_KEY"),
        app_id=os.getenv("ALIYUN_APP_ID_J"),  # 替换为实际的应用 ID
        prompt="nishishui")

    if response.status_code != HTTPStatus.OK:
        print(f'request_id={response.request_id}')
        print(f'code={response.status_code}')
        print(f'message={response.message}')
        print(f'请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code')
        return response

    responseNext = Application.call(
                # 若没有配置环境变量，可用百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
                api_key=os.getenv("ALIYUN_API_KEY"),
                app_id=os.getenv("ALIYUN_APP_ID_J"),  # 替换为实际的应用 ID
                prompt='如何看待2026年美伊战争走势?',
                session_id=response.output.session_id)  # 上一轮response的session_id

    if responseNext.status_code != HTTPStatus.OK:
        print(f'request_id={responseNext.request_id}')
        print(f'code={responseNext.status_code}')
        print(f'message={responseNext.message}')
        print(f'请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code')
    else:
        print('%s\n session_id=%s\n' % (responseNext.output.text, responseNext.output.session_id))
        # print('%s\n' % (response.usage))

if __name__ == '__main__':
    call_with_session()
    # import os
    # import dashscope
    #
    # messages = [
    #     {'role': 'system', 'content': 'You are a helpful assistant.'},
    #     {'role': 'user', 'content': '你是谁？'}
    # ]
    # response = dashscope.Generation.call(
    #     # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    #     api_key=os.getenv('ALIYUN_API_KEY'),
    #     model="qwen-plus",
    #     # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    #     messages=messages,
    #     result_format='message'
    # )
    # print(response)