import tkinter as tk
import speech_recognition as sr
import requests
import json
import csv
import pyaudio
from PIL import Image, ImageTk
recognizer = sr.Recognizer()

def start_voice_input():
    with sr.Microphone() as source:
        print("Please say something:")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio, language='ja-JP')
        aoi_anser = process_input_and_log(text)
        response_box.insert(tk.END, "あなたの質問: " + text + "\n" + "葵ちゃんからの解答:" + aoi_anser + "\n")
    except sr.UnknownValueError:
        response_box.insert(tk.END, "Could not understand audio\n")
    except sr.RequestError as e:
        response_box.insert(tk.END, "Error: {0}\n".format(e))
    pass

def send_to_chatgpt(text):
    api_key = load_api_key()
    aoi_set = load_aoi_setting()
    past_conversations = get_past_conversations()
    past_conversations.append({"role": "user", "content": aoi_set + text})
    headers = {
        "Authorization": f"Bearer {api_key}",
        'Content-type': 'application/json',
        'X-Slack-No-Retry': '1'
    }
    data = {
        "model": "gpt-4-1106-preview",
        "max_tokens": 1024,
        "temperature": 0.9, 
        "messages": past_conversations    
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None
    return response.json()

def log_to_csv(question, answer, filename="chat_history.csv"):
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        answer = answer.replace('\n', ' ')
        writer.writerow([question, answer])

def process_input_and_log(text):
    response = send_to_chatgpt(text)
    if response and "choices" in response and response["choices"]:
        answer = response["choices"][0].get("message").get("content")
        log_to_csv(text, answer)

        # VOICEVOX APIを使用して応答を音声に変換
        audio_data = text_to_speech(answer)
        pya = pyaudio.PyAudio()
    
        stream = pya.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=24000,
                        output=True)
        
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()
        pya.terminate()

        return answer
    else:
        return "No response or error occurred"
def load_api_key(filename="api_key.txt"):
    with open(filename, "r", encoding="utf-8") as file:
        return file.read().strip()

def load_aoi_setting(filename="aoi_setting.txt"):
    with open(filename, "r" , encoding="utf-8") as file:
        return file.read().strip()

def get_past_conversations(filename="chat_history.csv", max_conversations=8):
    conversations = []

    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        rows = list(reader)
        rows.reverse()  # 最新の行を先頭にする

        for row in rows[:max_conversations]:
            user_message = {'role': 'user', 'content': row[0]}
            system_message = {'role': 'system', 'content': row[1]}

            conversations.append(user_message)
            if system_message['content']:
                conversations.append(system_message)

    conversations.reverse()  # 元の順序に戻す
    return conversations

def text_to_speech(text, speaker_id=8):
    host = "127.0.0.1"
    port = 50021
    text = text.replace('\n', ' ')
    params = (
        ('text', text),
        ('speaker', speaker_id),
    )
    query = requests.post(
        f'http://{host}:{port}/audio_query',
        params=params
    )
    synthesis = requests.post(
        f'http://{host}:{port}/synthesis',
        headers = {"Content-Type": "application/json"},
        params = params,
        data = json.dumps(query.json())
    )
    audio_response = synthesis.content
    return audio_response

# ウィンドウの作成
window = tk.Tk()
window.title("葵ちゃん Interface")
window.geometry("600x300")  # ウィンドウの幅を増やします

# 画像の読み込みとサイズ調整
image = Image.open("character_image.png")
image = image.resize((130, 300), Image.Resampling.LANCZOS)  # 画像のサイズを調整
photo = ImageTk.PhotoImage(image)

# 画像ラベルの作成と配置
image_label = tk.Label(window, image=photo)
image_label.pack(side=tk.LEFT)

# ボタンの追加
start_button = tk.Button(window, text="Start Voice Input", command=start_voice_input)
start_button.pack(pady=10)

# テキストボックスの追加
response_box = tk.Text(window, height=10, width=50)
response_box.pack(pady=10)

# ウィンドウの実行
window.mainloop()