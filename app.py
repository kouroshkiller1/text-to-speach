# ۱. نصب پیش‌نیازها
import streamlit as st

import os
import io
import time
import gradio as gr
from google import genai
from google.genai import types
from pydub import AudioSegment

# بانک کامل تمام ۸ قالب آماده
TEMPLATES = {
    "📖 The Master Storyteller (راوی داستان و کتاب)": "تو یک راوی حرفه‌ای و داستان‌گوی مسلط هستی. متن را با لحنی عمیق، شمرده، احساسی و جذاب مانند یک کتاب صوتی حرفه‌ای بخوان.",
    "🤖 The Everyday Assistant (دستیار روزمره)": "تو یک دستیار هوشمند، مؤدب و کارآمد هستی. متن را با لحنی رسمی، شفاف، کمک‌کننده و مستقیم بخوان.",
    "🎮 The Guarded NPC (شخصیت محتاط بازی فانتزی)": "تو یک کاراکتر غیرقابل‌بازی (NPC) در یک دنیای ماجراجویی و فانتزی هستی. دیالوگ‌ها را با لحنی رازآلود، کمی محتاط، شکاک و متناسب با فضای نقش‌آفرینی بخوان.",
    "🎙️ The Energetic Co-Host (هم‌مجری پرانرژی)": "تو یک هم‌مجری پادکست پرانرژی و صمیمی هستی. متن را با لحنی شاداب، زنده، محاوره‌ای و پرانرژی بخوان.",
    "📢 The Ad Voiceover (گوینده تبلیغاتی تجاری)": "تو یک گوینده تیزرهای تبلیغاتی پرمیوم هستی. متن را با صدای بسیار روان، جذاب، ترغیب‌کننده و با کلاس کاری بالا بخوان.",
    "💼 The Training Guide (راهنمای آموزشی شرکتی)": "تو یک راهنمای آموزشی معتبر و رسمی هستی. متن را با لحنی واضح، قاطع، باصلابت و هدایت‌کننده برای آموزش سازمانی بخوان.",
    "🎯 The Game Show Host (مجری مسابقه هیجانی)": "تو مجری هیجان‌انگیز یک مسابقه تلویزیونی هستی. متن را با لحنی فوق‌العاده پرانرژی، نمایشی، بلند و هیجانی بخوان.",
    "👨‍🏫 The Patient Teacher (معلم صبور)": "تو یک معلم صبور، مهربان و مشوق هستی. متن را با لحنی آرام، شمرده، واضح و آموزش‌دهنده بخوان.",
    "✏️ سفارشی (دستی)": ""
}

def update_system_instruction(template_name):
    return TEMPLATES.get(template_name, "")

def convert_text_to_audiobook(
    api_key, text_input, file_obj, 
    model_name, voice_name, safety_level,
    temperature, top_p, top_k, max_tokens, presence_penalty, frequency_penalty,
    system_instruction, max_chars_per_chunk, 
    progress=gr.Progress()
):
    if not api_key.strip():
        return None, "❌ لطفاً API Key گوگل خود را وارد کنید."
    
    full_text = ""
    if file_obj is not None:
        try:
            with open(file_obj.name, "r", encoding="utf-8") as f:
                full_text = f.read()
        except Exception as e:
            return None, f"❌ خطا در خواندن فایل: {str(e)}"
    elif text_input.strip():
        full_text = text_input.strip()
    else:
        return None, "❌ لطفاً یک فایل متنی آپلود کنید یا متنی در کادر بنویسید."

    try:
        client = genai.Client(api_key=api_key.strip())
        
        paragraphs = full_text.split("\n")
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if not para.strip():
                continue
            if len(current_chunk) + len(para) < max_chars_per_chunk:
                current_chunk += para + "\n"
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n"
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        total_chunks = len(chunks)
        combined_audio = AudioSegment.empty()

        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold=safety_level),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold=safety_level),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold=safety_level),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold=safety_level),
        ]

        generation_config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            temperature=temperature,
            top_p=top_p,
            top_k=int(top_k),
            max_output_tokens=int(max_tokens),
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            safety_settings=safety_settings,
            system_instruction=system_instruction.strip() if system_instruction.strip() else None,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )

        for idx, chunk in enumerate(chunks):
            part_num = idx + 1
            progress((idx / total_chunks), desc=f"در حال ساخت پارت {part_num} از {total_chunks}...")
            
            prompt = f"متن زیر را بخوان:\n\n{chunk}"
            
            # سیستم تلاش مجدد خودکار فوق‌حرفه‌ای برای نسخه Pro
            max_retries = 5  # تا ۵ بار تلاش می‌کند
            
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=generation_config
                    )
                    
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            audio_data = part.inline_data.data
                            segment = AudioSegment.from_file(io.BytesIO(audio_data))
                            combined_audio += segment
                    
                    # اگر موفق شد، حلقه خطا را می‌شکند
                    break
                
                except Exception as req_error:
                    err_msg = str(req_error)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        if attempt < max_retries - 1:
                            # صبر طولانی‌تر (۱۵ ثانیه) برای مدل‌های Pro
                            progress((idx / total_chunks), desc=f"⚠️ محدودیت Pro! پارت {part_num}. صبر ۱۵ ثانیه و تلاش مجدد ({attempt+1}/{max_retries})...")
                            time.sleep(15)
                        else:
                            return None, f"❌ متاسفانه سقف مجاز گوگل کاملاً پر شده (پارت {part_num}). لطفا چند دقیقه دیگر تست کنید."
                    else:
                        return None, f"❌ خطای ناشناخته در پارت {part_num}: {err_msg}"
            
            # ایجاد تاخیر ثابت ۴ ثانیه‌ای بین پارت‌های موفق برای جلوگیری از خشم سرور!
            if idx < total_chunks - 1:
                progress((idx / total_chunks), desc=f"⏳ پارت {part_num} موفق بود. ۴ ثانیه استراحت تا پارت بعدی...")
                time.sleep(4)

        output_filename = "Audiobook_Pro_Max_Output.mp3"
        combined_audio.export(output_filename, format="mp3")
        
        return output_filename, f"✅ پردازش موفقیت‌آمیز! ({total_chunks} پارت ادغام شدند)."

    except Exception as e:
        return None, f"❌ خطایی رخ داد: {str(e)}"

# طراحی UI
with gr.Blocks(theme=gr.themes.Base(), title="Audio Studio Pro Max") as demo:
    gr.Markdown("# 🎙️ Google AI Studio: Text-to-Audio Edition (Pro Auto-Retry)")
    
    with gr.Row():
        with gr.Column(scale=1, variant="panel"):
            gr.Markdown("### ⚙️ تنظیمات اصلی")
            api_key_input = gr.Textbox(label="API Key", type="password", placeholder="AIzaSy...")
            
            model_dropdown = gr.Dropdown(
                choices=[
                    "gemini-2.5-pro-preview-tts", 
                    "gemini-2.0-flash", 
                    "gemini-2.0-flash-lite-preview-02-05", 
                    "gemini-1.5-pro",
                    "gemini-1.5-flash"
                ],
                value="gemini-2.5-pro-preview-tts", 
                label="نسخه مدل (Model)"
            )
            
            voice_dropdown = gr.Dropdown(
                choices=["Aoede", "Charon", "Fenrir", "Kore", "Puck"],
                value="Aoede", label="گوینده (Voice)"
            )
            
            safety_dropdown = gr.Dropdown(
                choices=["BLOCK_NONE", "BLOCK_ONLY_HIGH", "BLOCK_MEDIUM_AND_ABOVE", "BLOCK_LOW_AND_ABOVE"],
                value="BLOCK_NONE", label="🛡 فیلتر ایمنی (Safety Settings)"
            )

            gr.Markdown("### 🎭 قالب‌های آماده لحن (Quickstart Templates)")
            template_dropdown = gr.Dropdown(
                choices=list(TEMPLATES.keys()),
                value="📖 The Master Storyteller (راوی داستان و کتاب)",
                label="انتخاب سبک و لحن"
            )

            with gr.Accordion("⚙️ دستورالعمل سیستم (System Instruction)", open=True):
                system_instruction_input = gr.Textbox(
                    label="متن دستورالعمل", lines=4,
                    value=TEMPLATES["📖 The Master Storyteller (راوی داستان و کتاب)"]
                )

            with gr.Accordion("🛠 تنظیمات پیشرفته (Sampling)", open=False):
                temp_slider = gr.Slider(0.0, 2.0, value=0.3, step=0.1, label="دما (Temperature)")
                top_p_slider = gr.Slider(0.0, 1.0, value=0.95, step=0.01, label="Top-P")
                top_k_slider = gr.Slider(1, 100, value=40, step=1, label="Top-K")
                presence_penalty_slider = gr.Slider(-2.0, 2.0, value=0.0, step=0.1, label="جریمه حضور")
                freq_penalty_slider = gr.Slider(-2.0, 2.0, value=0.0, step=0.1, label="جریمه تکرار")
                max_tokens_slider = gr.Slider(1024, 8192, value=8192, step=1024, label="حداکثر توکن خروجی")

            chunk_size_slider = gr.Slider(
                500, 3000, value=1800, step=100, label="حداکثر طول هر پارت (Chunk Size)"
            )

        with gr.Column(scale=2):
            gr.Markdown("### 📝 محتوا و خروجی")
            
            with gr.Tabs():
                with gr.TabItem("✏️ نوشتن متن"):
                    text_area = gr.Textbox(
                        label="متن کتاب یا نوشته", lines=15,
                        placeholder="متن خود را اینجا وارد کنید..."
                    )
                with gr.TabItem("📄 آپلود فایل متنی"):
                    file_upload = gr.File(label="فایل TXT را آپلود کنید", file_types=[".txt"])
            
            submit_btn = gr.Button("▶️ Run (تولید فایل صوتی)", variant="primary", size="lg")
            
            gr.Markdown("---")
            status_output = gr.Textbox(label="وضعیت لاگ (Log)", interactive=False)
            audio_output = gr.Audio(label="پخش و دانلود خروجی نهایی", type="filepath")

    template_dropdown.change(
        fn=update_system_instruction,
        inputs=[template_dropdown],
        outputs=[system_instruction_input]
    )

    submit_btn.click(
        fn=convert_text_to_audiobook,
        inputs=[
            api_key_input, text_area, file_upload, 
            model_dropdown, voice_dropdown, safety_dropdown,
            temp_slider, top_p_slider, top_k_slider, max_tokens_slider, presence_penalty_slider, freq_penalty_slider,
            system_instruction_input, chunk_size_slider
        ],
        outputs=[audio_output, status_output]
    )

demo.launch(share=True, debug=True)
