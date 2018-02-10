from __future__ import unicode_literals

from flask import Flask, request, abort
import os, boto3, random, sys
from boto3.dynamodb.conditions import Key, Attr
from linebot import (
    LineBotApi, WebhookHandler, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FollowEvent, LocationMessage, TemplateSendMessage,
    ConfirmTemplate, PostbackTemplateAction, MessageTemplateAction, PostbackEvent, ButtonsTemplate
)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
aws_key_id = os.getenv('aws_access_key', None)
aws_secret_id = os.getenv('aws_secret_access_key', None)
aws_region = os.getenv('aws_region', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if aws_key_id is None:
    print('Specify aws_access_key as environment variable.')
    sys.exit(1)
if aws_secret_id is None:
    print('Specify aws_secret_access_key as environment variable.')
    sys.exit(1)
if aws_region is None:
    print('Specify aws_region as environment variable.')
    sys.exit(1)

app = Flask(__name__)
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)
dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                            aws_access_key_id=aws_key_id,
                            aws_secret_access_key=aws_secret_id)
website_name = 'thevagabond'
registering_question = ['ที่อยู่', 'อาชีพ']
registered = False
during_survey = False
current_user_id = ''
question = ''
done = False
point = 0
ans_count = 0

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global website_name
    global question
    global registering_question
    global registered
    global during_survey
    global done
    global point
    global ans_count
    global tips
    if(event.message.text != 'ยัง'):
        if (registered == False):
            # table = get_table('users')
            print("Answer: " + event.message.text)
            if (len(registering_question) != 0):
                messages = [registering_question.pop(0)]
                # if (event.message.text == 'ช'):
                    # table.update_item(Key={'user-id': get_current_user_id()}, AttributeUpdates={'gender': {'Value':'male','Action':'PUT'}})
                # elif (event.message.text == '10/04/1992'):
                    # table.update_item(Key={'user-id': get_current_user_id()}, AttributeUpdates={'dob': {'Value': event.message.text, 'Action': 'PUT'}, 'age':{'Value': 25, 'Action': 'PUT'}})
                # elif (event.message.type == 'location'):
                    # table.update_item(Key={'user-id': get_current_user_id()}, AttributeUpdates={'address': {'Value':event.message.address, 'Action':'PUT'}, 'latitude': {'Value':event.message.latitude, 'Action':'PUT'}, 'longitude': {'Value':event.message.longitude, 'Action':'PUT'}})
            else:
                # if (event.message.text == '4'):
                    # table.update_item(Key={'user-id': get_current_user_id()}, AttributeUpdates={'family-mem-no': {'Value':event.message.text, 'Action': 'PUT'}})
                registered = True
                messages = ['ยินดีด้วย คุณได้กรอกประวัติเรียบร้อยแล้ว!' ,'หากพร้อมแล้ว สามารถพิม "เริ่ม" ได้เลย']
        else:
            if(during_survey == True or event.message.text == 'เริ่ม'):
                # table = get_table('survey-answer')
                if not question and done is False:
                    question = get_questionnaire(get_current_user_id())
                if(len(question)!=0):
                    during_survey = True
                    messages = [question.pop(0)]
                    if (len(question) == 0):
                        done = True
                    if (event.message.text != 'เริ่ม'):
                        ans_count = ans_count + 1
                        print("Answer: " + event.message.text)
                        # table.put_item(Item={'survey-id':'s001', 'answer-id': ans_count, 'user-id': 1, 'ans': event.message.text})
                else:
                    ans_count = ans_count + 1
                    print("Answer: " + event.message.text)
                    # table.put_item(Item={'survey-id':'s001', 'answer-id': ans_count, 'user-id': 1, 'ans': event.message.text})
                    done = False
                    during_survey = False
                    point = point + 10
                    messages = ['Done!', 'ยินดีด้วย คุณได้ {} points!'.format(point), 'สามารถเช็คคะแนนล่าสุดของตัวเองได้โดยพิมว่า "คะแนน"']
            elif (event.message.text == 'คะแนน'):
                messages = ['ตอนนี้คุณมีคะแนนอยู่ทั้งหมด {} คะแนน'.format(point), 'หากต้องการแลกรางวัล สามารถพิม "{} ได้ทันที"'.format('แลกรางวัล')]
            elif (event.message.text == 'แลกรางวัล'):
                messages = ['แลกได้ที่ www.{}.com/redeem'.format(website_name)]
            elif (event.message.text == 'tips'):
                messages = [random.choice(tips)['text']]
            else:
                 messages = ['พิม "เริ่ม" ได้เสมอ เมื่อต้องการเริ่มเก็บคะแนนจากการทำแบบสอบถาม']
    else:
        messages = ['หากพร้อมแล้ว สามารถพิมคำว่า "สมัคร" ได้ตลอดเวลา']

    if (messages[0] != 'do you love energy'):
        line_bot_api.reply_message(
                    event.reply_token,
                    [TextSendMessage(text=msg) for msg in messages])
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TemplateSendMessage(alt_text='Buttons template',
                                template=ButtonsTemplate(
                                    title=messages[0],
                                    text='Please select',
                                    actions=[
                                        MessageTemplateAction(
                                            label='A lot',
                                            text='3'
                                        ),
                                        MessageTemplateAction(
                                            label='so so',
                                            text='2'
                                        ),
                                        MessageTemplateAction(
                                            label='nah',
                                            text='1'
                                        )
                                    ])
                                )
            )

@handler.add(FollowEvent)
def handle_message(event):
    global current_user_id
    profile = line_bot_api.get_profile(event.source.user_id)
    # table = get_table('users')
    current_user_id = gen_user_id()
    print("User name: " + profile.display_name)
    print("User line id: " + profile.user_id)
    # table.put_item(Item={'user-id':current_user_id, 'user-name':profile.display_name, 'user-line-id':profile.user_id})
    line_bot_api.reply_message(event.reply_token, TemplateSendMessage(
            alt_text='Confirm template',
            template=ConfirmTemplate(
                text='เริ่มใส่ประวัติเลยไหม?',
                actions=[
                    MessageTemplateAction(
                        label='เริ่ม',
                        text='สมัคร'
                    ),
                    MessageTemplateAction(
                        label='ไม่',
                        text='ยัง'
                    )
                ]
            )
        )
    )

@handler.add(MessageEvent, message=LocationMessage)
def handle_message(event):
    global registering_question
    print("User address: " + event.message.address)
    print("User address: {}".format(event.message.latitude))
    print("User address: {}".format(event.message.longitude))
    # line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(text=registering_question.pop(0)))
    line_bot_api.reply_message(
        event.reply_token,
        TemplateSendMessage(alt_text='Buttons template',
                            template=ButtonsTemplate(
                                title=registering_question.pop(0),
                                text='โปรดเลือก',
                                actions=[
                                    MessageTemplateAction(
                                        label='พนักงาน',
                                        text='พนักงาน'
                                    ),
                                    MessageTemplateAction(
                                        label='เจ้าของกิจการ',
                                        text='เจ้าของกิจการ'
                                    ),
                                    MessageTemplateAction(
                                        label='ชาวบ้าน',
                                        text='ชาวบ้าน'
                                    ),
                                    MessageTemplateAction(
                                        label='นักเรียน',
                                        text='นักเรียน'
                                    )
                                ])
                            )
        )

def get_questionnaire(userId):
    # user_profile = dynamodb.Table('users').query(KeyConditionExpression=Key('user-id').eq(1))['Items'][0]
    # question = dynamodb.Table('survey-question').query(KeyConditionExpression=Key('survey-id').eq('s001'))['Items']
    question = ['ราคาดีเซลวันนี้', 'do you love energy']
    return question

def get_table(table_name):
    return dynamodb.Table(table_name)

def gen_user_id():
    # table = get_table('users')
    return 1  # table.item_count + 1

def get_current_user_id():
    return current_user_id

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=int(os.environ.get('PORT', 5000)))
