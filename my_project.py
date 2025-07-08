import streamlit as st
import json
import requests
import contextlib
import io

with open("dsa_questions_updated.json", encoding="utf-8") as f:
    dsa_questions = json.load(f)

if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "last_question_id" not in st.session_state:
    st.session_state.last_question_id = ""

st.title("📘 Student Buddy - DSA App 💻")

topic = st.selectbox("📂 Select Topic", list(dsa_questions.keys()))
questions = dsa_questions[topic]
question = st.selectbox("❓ Select Question", [q["question"] for q in questions])
current_q = next(q for q in questions if q["question"] == question)

if st.session_state.last_question_id != current_q["id"]:
    st.session_state.attempts = 0
    st.session_state.last_question_id = current_q["id"]

st.markdown(f"**📈 Difficulty**: {current_q['difficulty']}")
st.markdown(f"""### ✏️ Your Task  
💡 **Sample Input:** `{current_q['sample_input']}`  
💡 **Expected Output:** `{current_q['expected_output']}`  
""")

mode = st.selectbox("⚙️ Select Mode", ["Offline Mode", "AI Assist"])
api_key = st.text_input("🔐 Enter your API Key", type="password") if mode == "AI Assist" else None

prefilled_code = f"""{current_q['function_signature']}
    # ✏️ Write your logic here
    return"""

code = st.text_area("🧠 Your Code", value=prefilled_code, height=250)

col1, col2, col3 = st.columns(3)
run_clicked = col1.button("▶️ Run Code")
hint_clicked = col2.button("💡 Show Hint")
show_opt = col3.button("🚀 Optimized Solution")

def strict_validation_prompt(question, code):
    return (
        f"Validate this Python function strictly.\n\n"
        f"Problem: {question}\n\n"
        f"Code:\n{code}\n\n"
        f"Rules:\n"
        f"- If code is empty → return: incorrect\n"
        f"- If code has syntax issues → return: incorrect\n"
        f"- If logic is incorrect or function name/params are wrong → return: incorrect\n"
        f"- If code is perfect and gives correct output → return: correct\n\n"
        f"Reply only with 'correct' or 'incorrect'. No explanation."
    )

def local_code_checker(code, input_data, expected_output):
    try:
        # Create a local namespace
        local_vars = {}
        # Define the function from user input
        exec(code, {}, local_vars)

        # Extract function name from the first line
        func_line = code.strip().split('\n')[0]
        func_name = func_line.split()[1].split('(')[0]

        # Prepare function call
        if "=" not in input_data:
            input_str = input_data.strip()
            call_code = f"result = {func_name}({input_str})"
        else:
            setup_code = input_data.strip()
            call_code = f"{setup_code}\nresult = {func_name}("

            # Auto-extract parameters from signature
            params = func_line.split('(')[1].split(')')[0].split(',')
            param_values = [p.strip().split('=')[0] for p in params if p.strip()]
            call_code += ', '.join(param_values) + ")"

        # Redirect stdout just in case
        with contextlib.redirect_stdout(io.StringIO()):
            exec(call_code, {}, local_vars)

        result = local_vars.get("result")
        return str(result) == str(expected_output)
    except Exception:
        return False

def call_ai_api(api, api_key, prompt, mode):
    if mode == "Offline Mode":
        if "hint" in prompt.lower():
            return current_q["hint"]
        elif "explain" in prompt.lower():
            return current_q["optimized_explanation"]
        elif "optimized" in prompt.lower():
            return current_q["optimized_code"]
        elif "validate" in prompt.lower():
            return "correct" if local_code_checker(code, current_q['sample_input'], current_q['expected_output']) else "incorrect"
        return "Offline fallback."

    elif api == "DeepSeek":
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "deepseek-coder",
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            else:
                return f"Error: {response.text}"
        except Exception as e:
            return f"Exception: {str(e)}"

if run_clicked and code.strip():
    prompt = strict_validation_prompt(current_q['question'], code)
    result = call_ai_api(mode, api_key, prompt, mode)

    if result and result.lower().strip() == "correct":
        st.success("✅ Code logic is correct")
        st.markdown(f"📊 **Time Complexity:** {current_q['user_tc']}")
        st.markdown(f"📦 **Space Complexity:** {current_q['user_sc']}")
        st.session_state.attempts = 0
    else:
        st.session_state.attempts += 1
        st.error("❌ AI suggests your code might be wrong")
        if st.session_state.attempts >= 2:
            st.warning("📌 Showing correct solution after 2 failed attempts:")
            st.code(current_q["optimized_code"])
            st.markdown(f"📘 **Explanation (5 lines):**\n{current_q['optimized_explanation']}")

if hint_clicked:
    st.info("💡 " + current_q["hint"])

if show_opt:
    st.code(current_q["optimized_code"])
    st.markdown(f"📘 **Explanation (5 lines):**\n{current_q['optimized_explanation']}")
    st.markdown(f"📊 **Time Complexity:** {current_q['optimized_tc']}")
    st.markdown(f"📦 **Space Complexity:** {current_q['optimized_sc']}")
