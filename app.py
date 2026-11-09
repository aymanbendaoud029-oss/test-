import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime, date
import pandas as pd
from google import genai

# ================= ====================
# 1. إعدادات الصفحة وقاعدة البيانات
# ================= ====================
st.set_page_config(
    page_title="منصة دراستي الذكية",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إنشاء وتوصيل قاعدة البيانات
conn = sqlite3.connect('study_smart.db', check_same_thread=False)
c = conn.cursor()

# إنشاء الجداول الأساسية
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)''')

c.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    subject TEXT,
    title TEXT,
    due_date TEXT,
    status TEXT DEFAULT 'قيد الانتظار',
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')

c.execute('''
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    subject TEXT,
    exam_date TEXT,
    hall TEXT,
    notes TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')

c.execute('''
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    content TEXT,
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')
conn.commit()

# ================= ====================
# 2. وظائف الحماية والذكاء الاصطناعي
# ================= ====================
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def get_gemini_client(api_key):
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        return None

# ================= ====================
# 3. إدارة الجلسة (Session State)
# ================= ====================
if 'user' not in st.session_state:
    st.session_state.user = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# ================= ====================
# 4. واجهات تسجيل الدخول وإنشاء الحساب
# ================= ====================
if not st.session_state.user:
    st.title("🎓 منصة دراستي الذكية (StudySmart)")
    st.write("أهلاً بك! يرجى تسجيل الدخول أو إنشاء حساب جديد للوصول إلى أدواتك الدراسية.")
    
    tab_login, tab_signup = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])
    
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            submit = st.form_submit_button("دخول")
            
            if submit:
                c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
                user_data = c.fetchone()
                if user_data and check_password(password, user_data[1]):
                    st.session_state.user = {"id": user_data[0], "username": username}
                    st.success(f"مرحباً بك {username}!")
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")
                    
    with tab_signup:
        with st.form("signup_form"):
            new_user = st.text_input("اختر اسم مستخدم")
            new_pass = st.text_input("اختر كلمة مرور", type="password")
            confirm_pass = st.text_input("تأكيد كلمة المرور", type="password")
            submit_signup = st.form_submit_button("إنشاء حساب")
            
            if submit_signup:
                if not new_user or not new_pass:
                    st.warning("يرجى ملء جميع الحقول.")
                elif new_pass != confirm_pass:
                    st.error("كلمتا المرور غير متطابقتين.")
                else:
                    try:
                        hashed = hash_password(new_pass)
                        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_user, hashed))
                        conn.commit()
                        st.success("تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول.")
                    except sqlite3.IntegrityError:
                        st.error("اسم المستخدم مستخدم بالفعل. اختر اسماً آخر.")

# ================= ====================
# 5. الواجهة الرئيسية (بعد تسجيل الدخول)
# ================= ====================
else:
    user_id = st.session_state.user["id"]
    username = st.session_state.user["username"]
    
    # القائمة الجانبية
    with st.sidebar:
        st.title(f"👤 {username}")
        st.write("---")
        menu = st.radio("انتقل إلى:", [
            "📊 لوحة التحكم",
            "📅 الأجندة والمهام",
            "📝 جدول الامتحانات",
            "📒 المذكرة الذكية",
            "🤖 مساعد Gemini الدراسي"
        ])
        
        st.write("---")
        api_key = st.text_input("مفتاح Google Gemini API:", type="password", help="أدخل مفتاح API لاستخدام خدمات الذكاء الاصطناعي")
        
        if st.button("تسجيل الخروج"):
            st.session_state.user = None
            st.rerun()
            
    # --- 1. لوحة التحكم ---
    if menu == "📊 لوحة التحكم":
        st.header("📊 لوحة التحصيل الدراسي")
        
        # جلب الإحصائيات
        c.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'مكتملة'", (user_id,))
        completed_tasks = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'قيد الانتظار'", (user_id,))
        pending_tasks = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM exams WHERE user_id = ?", (user_id,))
        total_exams = c.fetchone()[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("المهام المكتملة", completed_tasks)
        col2.metric("المهام المتبقية", pending_tasks)
        col3.metric("الامتحانات المسجلة", total_exams)
        
        st.write("---")
        st.subheader("💡 نصيحة دراسية اليوم")
        st.info("قسم موادك الدراسية إلى فترات زمنية مدتها 25 دقيقة (تقنية البومودورو) للحفاظ على أعلى درجات التركيز.")

    # --- 2. الأجندة والمهام ---
    elif menu == "📅 الأجندة والمهام":
        st.header("📅 الأجندة وإدارة الواجبات")
        
        with st.expander("➕ إضافة مهام/واجبات جديدة"):
            with st.form("add_task"):
                subject = st.text_input("اسم المادة")
                title = st.text_input("وصف المهمة / الواجب")
                due_date = st.date_input("تاريخ التسليم", min_value=date.today())
                submit_task = st.form_submit_button("حفظ المهمة")
                
                if submit_task and subject and title:
                    c.execute("INSERT INTO tasks (user_id, subject, title, due_date) VALUES (?, ?, ?, ?)",
                              (user_id, subject, title, str(due_date)))
                    conn.commit()
                    st.success("تمت إضافة المهمة بنجاح!")
                    st.rerun()

        st.subheader("قائمة المهام")
        tasks = pd.read_sql_query("SELECT id, subject as المادة, title as المهمة, due_date as التاريخ, status as الحالة FROM tasks WHERE user_id = ?", conn, params=(user_id,))
        
        if not tasks.empty:
            st.dataframe(tasks, use_container_width=True)
            
            # تحديث حالة مهمة
            task_to_update = st.selectbox("تغيير حالة مهمة:", tasks['id'].tolist(), format_func=lambda x: f"مهمة رقم #{x}")
            new_status = st.selectbox("الحالة الجديدة:", ["قيد الانتظار", "مكتملة"])
            if st.button("تحديث الحالة"):
                c.execute("UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?", (new_status, task_to_update, user_id))
                conn.commit()
                st.success("تم تحديث المهمة!")
                st.rerun()
        else:
            st.info("لا يوجد مهام مسجلة حالياً.")

    # --- 3. جدول الامتحانات ---
    elif menu == "📝 جدول الامتحانات":
        st.header("📝 جدول الامتحانات والعد التنازلي")
        
        with st.expander("➕ إضافة امتحان جديد"):
            with st.form("add_exam"):
                ex_subject = st.text_input("المادة الدراسية")
                ex_date = st.date_input("تاريخ الامتحان", min_value=date.today())
                ex_hall = st.text_input("قاعة الامتحان / المكان")
                ex_notes = st.text_area("ملاحظات المراجعة")
                submit_exam = st.form_submit_button("حفظ الامتحان")
                
                if submit_exam and ex_subject:
                    c.execute("INSERT INTO exams (user_id, subject, exam_date, hall, notes) VALUES (?, ?, ?, ?, ?)",
                              (user_id, ex_subject, str(ex_date), ex_hall, ex_notes))
                    conn.commit()
                    st.success("تم إدراج الامتحان بالجدول!")
                    st.rerun()

        c.execute("SELECT subject, exam_date, hall, notes FROM exams WHERE user_id = ? ORDER BY exam_date ASC", (user_id,))
        exams = c.fetchall()
        
        if exams:
            for ex in exams:
                exam_dt = datetime.strptime(ex[1], "%Y-%m-%d").date()
                days_left = (exam_dt - date.today()).days
                
                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.subheader(f"📌 {ex[0]}")
                        st.write(f"📅 التاريخ: {ex[1]} | 🏛️ القاعة: {ex[2]}")
                        if ex[3]:
                            st.caption(f"ملاحظات: {ex[3]}")
                    with col_b:
                        if days_left == 0:
                            st.error("⚠️ الامتحان اليوم!")
                        elif days_left > 0:
                            st.warning(f"متبقي: {days_left} يوم")
                        else:
                            st.gray("انتهى")
                    st.write("---")
        else:
            st.info("لم تقم بإضافة أي امتحانات بعد.")

    # --- 4. المذكرة الذكية ---
    elif menu == "📒 المذكرة الذكية":
        st.header("📒 المذكرة الرقمية وتلخيص النصوص")
        
        with st.form("save_note"):
            note_title = st.text_input("عنوان الملاحظة")
            note_content = st.text_area("محتوى الدرس أو الملاحظات", height=200)
            submit_note = st.form_submit_button("حفظ في المذكرة")
            
            if submit_note and note_title and note_content:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute("INSERT INTO notes (user_id, title, content, created_at) VALUES (?, ?, ?, ?)",
                          (user_id, note_title, note_content, now))
                conn.commit()
                st.success("تم حفظ الملاحظة!")
                st.rerun()
                
        st.subheader("ملاحظاتي المحفوظة")
        c.execute("SELECT id, title, content, created_at FROM notes WHERE user_id = ? ORDER BY id DESC", (user_id,))
        saved_notes = c.fetchall()
        
        for n in saved_notes:
            with st.expander(f"📖 {n[1]} ({n[3]})"):
                st.write(n[2])
                
                # خاصية التلخيص بـ Gemini
                if st.button(f"✨ تلخيص الملاحظة عبر Gemini", key=f"sum_{n[0]}"):
                    if not api_key:
                        st.error("يرجى إدخال مفتاح Gemini API في القائمة الجانبية أولاً.")
                    else:
                        client = get_gemini_client(api_key)
                        if client:
                            with st.spinner("جاري تلخيص النص..."):
                                prompt = f"قم بتلخيص الملاحظات الدراسية التالية في نقاط رئيسية واضحة:\n{n[2]}"
                                response = client.models.generate_content(
                                    model="gemini-2.5-flash",
                                    contents=prompt
                                )
                                st.markdown("**الملخص الذكي:**")
                                st.write(response.text)

    # --- 5. مساعد Gemini الدراسي ---
    elif menu == "🤖 مساعد Gemini الدراسي":
        st.header("🤖 المساعد الدراسي الذكي (Gemini AI)")
        st.write("اسأل عن شرح المفاهيم الصعبة، خطط المذاكرة، أو طلب أسئلة مراجعة.")
        
        # عرض المحادثات السابقة
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        user_input = st.chat_input("اكتب سؤالك الدراسي هنا...")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)
                
            if not api_key:
                st.error("يرجى أدخل مفتاح Gemini API في القائمة الجانبية لاستخدام المساعد الذكي.")
            else:
                client = get_gemini_client(api_key)
                if client:
                    with st.chat_message("assistant"):
                        with st.spinner("جاري التفكير..."):
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=user_input
                            )
                            st.write(response.text)
                            st.session_state.chat_history.append({"role": "assistant", "content": response.text})