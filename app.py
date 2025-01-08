# -----------------------------
# 3) OpenAI Chat Setup
# -----------------------------
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

openai.api_key = OPENAI_API_KEY

# Chat memory
MAX_MEMORY = 20
conversation_memory = []

# A big system prompt describing the entire system
system_context = """You are an AI assistant for a Facial Recognition Attendance system.
Facial Recognition Attendance system features:

1) AWS Rekognition:
   - We keep a 'students' collection on startup.
   - /register indexes a face by (name + student_id).
   - /recognize detects faces in an uploaded image, logs attendance in Firestore if matched.

2) Attendance:
   - Firestore 'attendance' collection: { student_id, name, timestamp, subject_id, subject_name, status='PRESENT' }.
   - UI has tabs: Register, Recognize, Subjects, Attendance (Bootstrap + DataTables).
   - Attendance can filter, inline-edit, download/upload Excel.

3) Subjects:
   - We can add subjects to 'subjects' collection, referenced in recognition.

4) Multi-Face:
   - If multiple recognized faces, each is logged to attendance.

5) Chat:
   - You are the assistant, guiding usage or code features.
"""

# Start the conversation with a system message
conversation_memory.append({"role": "system", "content": system_context})

# -----------------------------
# 13) OpenAI Chat Endpoint
# -----------------------------
@app.route("/process_prompt", methods=["POST"])
@login_required
@role_required(['admin'])  # Only admin can use chat
def process_prompt():
    data = request.json
    user_prompt = data.get("prompt","").strip()
    if not user_prompt:
        return jsonify({"error":"No prompt provided"}), 400

    # Add user message
    conversation_memory.append({"role": "user", "content": user_prompt})

    try:
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_memory
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        assistant_reply = response.choices[0].message.content.strip()
    except Exception as e:
        assistant_reply = f"Error generating response: {str(e)}"

    # Add assistant reply
    conversation_memory.append({"role": "assistant", "content": assistant_reply})

    # Maintain conversation memory limit
    if len(conversation_memory) > MAX_MEMORY:
        # Keep system message and last (MAX_MEMORY-1) messages
        conversation_memory = [conversation_memory[0]] + conversation_memory[-(MAX_MEMORY-1):]

    return jsonify({"message": assistant_reply}) 