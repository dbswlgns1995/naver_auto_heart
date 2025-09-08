import tkinter as tk
from time import sleep
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import pyperclip
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import tkinter.ttk as ttk
import random
import json
import os

DATA_FILE = "entry_data.json"
maxneighbornum = 150
default_scroll_time = 300
driver = None  # 전역으로 선언해 로그인 후 재사용


def create_driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--remote-debugging-port=9222')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return webdriver.Chrome(options=options)


def naver_login(driver, user_id, user_pw):
    driver.get("https://nid.naver.com/nidlogin.login")
    time.sleep(1)
    id_input = driver.find_element(By.ID, "id")
    id_input.click()
    pyperclip.copy(user_id)
    id_input.send_keys(Keys.CONTROL, 'v')
    time.sleep(1)
    pw_input = driver.find_element(By.ID, "pw")
    pw_input.click()
    pyperclip.copy(user_pw)
    pw_input.send_keys(Keys.CONTROL, 'v')
    time.sleep(1)
    driver.find_element(By.ID, "log\.login").click()
    time.sleep(2)


def login_button_click():
    global driver
    user_id = entry_id.get()
    user_pw = entry_pw.get()
    if not user_id or not user_pw:
        messagebox.showwarning("입력 오류", "아이디와 비밀번호를 모두 입력하세요.")
        return

    def run_login():
        global driver
        try:
            driver = create_driver()
            login_btn["state"] = "disabled"
            naver_login(driver, user_id, user_pw)
        except Exception as e:
            messagebox.showerror("오류", f"로그인 중 오류 발생: {e}")

    threading.Thread(target=run_login).start()


def login_complete_button_click():
    show_post_login_ui()


def show_post_login_ui():
    login_btn.grid_remove()
    login_complete_btn.grid_remove()
    entry_id.config(state='disabled')
    entry_pw.config(state='disabled')
    btn_neighbor_blog.grid(row=3, column=0, padx=10, pady=10)


def neighborNewFeed(maxnum, max_scroll_time=300):
    driver.get("https://m.blog.naver.com/FeedList.naver")
    start_time = time.time()
    card_xpath = '//ul[contains(@class,"x_uDS")]//div[@class="card__reUkU"]'
    unliked_blog_xpath = '//ul[contains(@class,"x_uDS")]//div[@role="presentation"]//a'
    fotter_blog_xpath = '//ul[contains(@class,"x_uDS")]//div[@class="meta_foot__GLrD8"]//a'
    neighborBlogs = driver.find_elements(By.XPATH, unliked_blog_xpath)
    last_len = 0

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        neighborBlogs = driver.find_elements(By.XPATH, card_xpath)
        heartPlaths = driver.find_elements(By.XPATH, fotter_blog_xpath)

        stop_flag = False
        for blog in heartPlaths:
            try:
                li_elem = blog.find_element(By.XPATH, './ancestor::li[1]')
                like_btn = li_elem.find_element(By.XPATH, './/a[@data-type="like"]')
                pressed = like_btn.get_attribute("aria-pressed")
            except:
                pressed = None
            print(pressed)
            if pressed == "true":
                print("좋아요(aria-pressed=true) 발견! 스크롤 중단")
                stop_flag = True
                break

        current_len = len(neighborBlogs)
        if stop_flag:
            break
        last_len = current_len

    blog_items = []
    for blog in neighborBlogs:
        try:
            # 1) URL 찾기: presentation 하위의 a 태그
            link_elem = blog.find_element(By.XPATH, './/div[@role="presentation"]//a')
            href = link_elem.get_attribute('href')
            # 2) 좋아요 버튼 찾기: meta_foot__GLrD8 하위의 data-type="like"
            like_btn = blog.find_element(By.XPATH, './/div[contains(@class,"meta_foot__GLrD8")]//a[@data-type="like"]')
            pressed = like_btn.get_attribute("aria-pressed")
            if pressed == "false":
                blog_items.append(("title", href))
        except Exception as e:
            print("오류 발생:", e)
            continue

    print(blog_items)
    return blog_items


def btn_neighbor_blog_click():
    global driver
    if not driver:
        messagebox.showwarning("경고", "먼저 로그인 해주세요.")
        return

    scroll_time = default_scroll_time

    progress_win = tk.Toplevel(root)
    progress_win.title("진행 중...")
    progress_label = tk.Label(progress_win, text="검색 중...")
    progress_label.pack(padx=20, pady=5)
    progress_bar = ttk.Progressbar(progress_win, mode='determinate', length=300)
    progress_bar.pack(padx=20, pady=20)

    def task():
        try:
            blog_items = neighborNewFeed(maxneighbornum, max_scroll_time=scroll_time)
            if len(blog_items) == 0:
                progress_win.destroy()
                root.after(0, lambda: messagebox.showinfo("알림", "공감할 글이 없습니다. 바쁘게 살았노."))
                return
            messagebox.showinfo("알림", f"총 {len(blog_items)} 개 발견!")
            progress_win.destroy()
            root.after(0, lambda: show_new_page(blog_items))
        finally:
            pass

    threading.Thread(target=task).start()


def show_blog_urls(blog_items):
    right_frame = tk.Frame(root)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    label_urls = tk.Label(right_frame, text="이웃 글 URL 목록")
    label_urls.pack()

    url_text = tk.Text(right_frame, height=20, width=60)
    url_text.pack()

    for _, url in blog_items:
        if url:
            url_text.insert(tk.END, url + "\n")

    url_text.config(state=tk.DISABLED)


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [""] * 5  # 기본값 5개 빈 문자열


def save_data(values):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(values, f, ensure_ascii=False, indent=2)


def show_new_page(blog_items):
    for widget in root.winfo_children():
        widget.destroy()

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    total_len = len(blog_items)

    label_desc = tk.Label(
        frame,
        text=(
            f"총 {total_len}개의 블로그 발견!"
            "\n5개의 댓글 중 랜덤으로 하나가 작성 됩니다. [빈 댓글은 무시]"
            "\n뀨뀨뀨는 블로그 주인장의 닉네임으로 치환 (ex: 뀨뀨뀨님 좋은 하루 보내세요 -> 따뜻한 이야기님 좋은 하루 보내세요)"
            "\n댓글 사용 체크 안할 시 공감만 누름"
        )
    )
    label_desc.pack(pady=10)

    text_boxes = []
    saved_values = load_data()

    for i in range(5):
        t = tk.Text(frame, width=40, height=3, wrap="word")
        t.pack(pady=5)
        if i < len(saved_values) and saved_values[i]:
            t.insert("1.0", saved_values[i])
        text_boxes.append(t)
        add_context_menu(t)

    check_var = tk.BooleanVar()
    chk = tk.Checkbutton(frame, text="댓글 사용", variable=check_var)
    chk.pack(pady=10)

    def wait_manual_login(drv, timeout=180):
        drv.get("https://nid.naver.com/nidlogin.login")
        wait = WebDriverWait(drv, timeout)
        wait.until(lambda d: "nid.naver.com" not in d.current_url and "login" not in d.current_url)
        return True

    def on_button_click():
        global driver
        values = [t.get("1.0", "end-1c") for t in text_boxes]
        use_comments = check_var.get()
        save_data(values)

        # 1) 드라이버 생성 및 로그인 확인
        if driver is None:
            driver = create_driver()
            try:
                wait_manual_login(driver, timeout=180)
            except Exception as e:
                messagebox.showerror("로그인 실패", f"로그인 대기 중 오류: {e}")
                return

        # 2) 모든 블로그에 대해 공감 및 댓글 작업 시작
        start_blog_processing(blog_items, values, use_comments)

    btn = tk.Button(frame, text="공감 및 댓글 달기 시작", command=on_button_click)
    btn.pack(pady=10)


def start_blog_processing(blog_items, comment_texts, use_comments):
    """모든 블로그에 대해 공감 및 댓글 작업을 진행하는 함수"""
    total = len(blog_items)

    # 진행상황 표시 창
    progress_win = tk.Toplevel(root)
    progress_win.title("블로그 처리 중...")
    progress_label = tk.Label(progress_win, text="준비 중...")
    progress_label.pack(padx=20, pady=5)
    progress_bar = ttk.Progressbar(progress_win, mode='determinate', length=400)
    progress_bar.pack(padx=20, pady=20)
    progress_bar['maximum'] = total

    def process_blogs():
        success_count = 0
        for idx, (title, url) in enumerate(blog_items, start=1):
            if not url:
                continue

            try:
                # 진행상황 업데이트
                root.after(0, lambda i=idx: progress_label.config(text=f"처리 중: {i}/{total}"))
                root.after(0, lambda i=idx: progress_bar.config(value=i))

                print(f"\n=== 블로그 {idx}/{total} 처리 시작 ===")
                print(f"URL: {url}")

                # 블로그 페이지 이동
                driver.get(url)
                time.sleep(random.randint(3, 7))  # 랜덤 대기
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                # 1) 공감 버튼 찾기 및 클릭
                like_success = click_like_button_original(driver, url)

                time.sleep(random.randint(5, 15))

                # 2) 댓글 작성 (체크박스가 활성화된 경우에만)
                comment_success = False
                if use_comments and like_success:
                    comment_success = process_comment(driver, url, comment_texts)

                if like_success or comment_success:
                    success_count += 1
                    print(f"블로그 처리 완료 - 공감: {like_success}, 댓글: {comment_success}")
                else:
                    print("블로그 처리 실패")

                # 다음 블로그 처리 전 대기
                time.sleep(random.randint(5, 10))

            except Exception as e:
                print(f"블로그 처리 중 오류 ({url}): {e}")
                continue

        # 완료 메시지
        root.after(0, lambda: messagebox.showinfo("완료",
                                                  f"모든 블로그 처리 완료!\n성공: {success_count}/{total}"))
        root.after(0, progress_win.destroy)
        root.after(0, reset_to_login_ui)

    # 백그라운드에서 처리
    threading.Thread(target=process_blogs).start()


def reset_to_login_ui():
    """모든 위젯 파괴 후 초기 로그인 UI 복원, show_post_login_ui 호출"""

    # 1. 기존 위젯 모두 파괴
    for widget in root.winfo_children():
        widget.destroy()

    btn_neighbor_blog = tk.Button(root, text="블로그 확인", command=btn_neighbor_blog_click)
    btn_neighbor_blog.grid(row=3, column=0, padx=10, pady=10)


# def like_all_blogs_with_progress(blog_items, win, label, bar):
#     total = len(blog_items)
#     bar['maximum'] = total
#
#     def task():
#         for idx, (title, url) in enumerate(blog_items, start=1):
#             if not url:
#                 continue
#             try:
#
#
#             except Exception as e:
#                 print(f"오류 발생 ({url}): {e}")
#
#             # 진행 상황 업데이트는 메인 스레드에서 실행
#             root.after(0, lambda i=idx: label.config(text=f"진행 중: {i}/{total} 개"))
#             root.after(0, lambda i=idx: bar.config(value=i))
#
#         # 완료 메시지도 메인 스레드에서
#         root.after(0, lambda: messagebox.showinfo("완료", "모든 블로그 공감 완료!"))
#         root.after(0, win.destroy)
#
#     threading.Thread(target=task).start()


def click_like_button_original(driver, url):
    try:
        driver.get(url)
        time.sleep(random.randint(5, 15))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        selectors = [
            '//*[contains(@id,"area_sympathy")]//a',
            '//*[contains(@id,"sympathy")]//a',
            'a[class*="likeit"]',
            'a[class*="sympathy"]',
            'a[onclick*="sympathy"]',
            'a[href*="sympathy"]',
        ]

        like_button = None
        for selector in selectors:
            try:
                if selector.startswith('/'):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    like_button = elements[0]
                    break
            except:
                continue

        if like_button and like_button.get_attribute("aria-pressed") != "true":
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", like_button)
            time.sleep(1)
            return True
        else:
            return False

    except Exception as e:
        print(f"공감 버튼 처리 오류: {e}")
        return False


def process_comment(driver, blog_url, comment_texts):
    """매번 랜덤으로 댓글을 선택해서 작성하는 함수"""
    try:
        # 매번 새로운 랜덤 댓글 선택
        candidates = [t.strip() for t in comment_texts if t and t.strip()]
        if not candidates:
            print("사용 가능한 댓글 텍스트가 없음")
            return False

        # 매번 랜덤 선택
        chosen_text = random.choice(candidates)
        print(f"선택된 댓글: {chosen_text}")

        # 작성자 이름 추출 시도
        author = extract_author_from_current_page(driver)

        # 뀨뀨뀨 치환
        if "뀨뀨뀨" in chosen_text and author:
            chosen_text = chosen_text.replace("뀨뀨뀨", author)
            print(f"작성자 치환 후: {chosen_text}")

        # 댓글 작성
        return write_comment_to_blog(driver, blog_url, chosen_text)

    except Exception as e:
        print(f"댓글 처리 오류: {e}")
        return False


def extract_author_from_current_page(driver):
    """현재 페이지에서 블로그 작성자 이름을 추출"""
    try:
        # 다양한 작성자 이름 셀렉터들
        selectors = [
            ".blog_author strong",
            ".author_name",
            ".writer_name",
            "[class*='author'] strong",
            "[class*='writer'] strong",
            ".nick strong"
        ]

        for selector in selectors:
            try:
                author_elem = driver.find_element(By.CSS_SELECTOR, selector)
                author = author_elem.text.strip()
                if author:
                    print(f"작성자 이름 추출: {author}")
                    return author
            except:
                continue

        print("작성자 이름을 찾을 수 없음")
        return None

    except Exception as e:
        print(f"작성자 이름 추출 오류: {e}")
        return None


def write_comment_to_blog(driver, blog_url, comment_text):
    """특정 블로그에 댓글을 작성하는 함수"""
    try:
        # URL에서 blogId와 logNo 추출
        if "blogId=" in blog_url and "logNo=" in blog_url:
            # URL 파싱
            import urllib.parse
            parsed_url = urllib.parse.urlparse(blog_url)
            params = urllib.parse.parse_qs(parsed_url.query)

            blog_id = params.get('blogId', [None])[0]
            log_no = params.get('logNo', [None])[0]

            if blog_id and log_no:
                # 댓글 페이지 URL 생성
                comment_url = f"https://m.blog.naver.com/CommentList.naver?blogId={blog_id}&logNo={log_no}"
                print(f"댓글 페이지로 이동: {comment_url}")

                # 댓글 작성 실행
                return write_comment_once(driver, comment_text, comment_url)

        print("URL에서 blogId 또는 logNo를 추출할 수 없음")
        return False

    except Exception as e:
        print(f"댓글 작성 URL 처리 오류: {e}")
        return False


def write_comment_once(driver, final_text: str, comment_url: str, timeout=15) -> bool:
    print(f"=== 댓글 작성 시작 ===")
    print(f"작성할 텍스트: {final_text}")

    wait = WebDriverWait(driver, timeout)
    driver.get(comment_url)
    time.sleep(2)  # 페이지 로딩 대기

    print(f"현재 URL: {driver.current_url}")

    # 1) iframe 확인 및 전환 (선택사항)
    try:
        iframe = driver.find_element(By.CSS_SELECTOR, "iframe")
        print("iframe 발견, 전환합니다.")
        driver.switch_to.frame(iframe)
    except Exception:
        print("iframe 없음, 현재 페이지에서 작업합니다.")

    # 2) 댓글 입력 영역 찾기 - HTML 구조에 맞춘 정확한 셀렉터
    try:
        editor = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div#naverComment__write_textarea[contenteditable='true']")))
        print("댓글 입력창 찾았습니다.")
    except Exception as e:
        print(f"댓글 입력창 찾기 실패: {e}")
        try:
            editor = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[contenteditable='true']")))
            print("일반 contenteditable 요소를 찾았습니다.")
        except Exception as e2:
            print(f"contenteditable 요소 찾기 실패: {e2}")
            return False

    # 3) 가이드 텍스트 요소 찾기
    try:
        guide = driver.find_element(By.CSS_SELECTOR, "div.u_cbox_guide[data-action='write#placeholder']")
        print("가이드 텍스트 요소 찾았습니다.")
    except Exception:
        print("가이드 텍스트 요소 없음.")
        guide = None

    # 4) 페이지 스크롤 (scrollIntoView 완전 제거)
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        print("페이지 하단으로 스크롤 완료.")
    except Exception as e:
        print(f"스크롤 오류 (무시): {e}")

    # 5) 가이드 요소 클릭으로 입력창 활성화
    if guide:
        try:
            print("가이드 텍스트 클릭으로 입력창 활성화 시도...")
            guide.click()
            time.sleep(1)
        except Exception as e:
            print(f"가이드 클릭 실패: {e}")
            try:
                driver.execute_script("arguments[0].click();", guide)
                time.sleep(1)
                print("JavaScript로 가이드 클릭 성공.")
            except Exception as e2:
                print(f"JavaScript 가이드 클릭도 실패: {e2}")

    # 6) 입력창 클릭 및 포커스
    try:
        print("입력창 클릭 및 포커스 설정...")
        editor.click()
        time.sleep(0.5)
        driver.execute_script("arguments[0].focus();", editor)
        time.sleep(0.5)
    except Exception as e:
        print(f"입력창 클릭/포커스 오류: {e}")
        try:
            driver.execute_script("arguments[0].click(); arguments[0].focus();", editor)
            time.sleep(1)
        except Exception as e2:
            print(f"JavaScript 클릭/포커스도 실패: {e2}")

    # 7) 텍스트 입력 - 여러 방법 시도
    success = False

    # 방법 1: send_keys 사용
    try:
        print("방법 1: send_keys로 텍스트 입력 시도...")
        editor.clear()
        editor.send_keys(final_text)
        time.sleep(1)
        success = True
        print("send_keys로 텍스트 입력 성공!")
    except Exception as e:
        print(f"send_keys 실패: {e}")

    # 방법 2: JavaScript innerHTML/textContent 사용
    if not success:
        try:
            print("방법 2: JavaScript로 텍스트 설정 시도...")
            driver.execute_script("arguments[0].innerHTML = arguments[1];", editor, final_text)
            time.sleep(0.5)
            driver.execute_script("arguments[0].textContent = arguments[1];", editor, final_text)
            success = True
            print("JavaScript로 텍스트 설정 성공!")
        except Exception as e:
            print(f"JavaScript 텍스트 설정 실패: {e}")

    # 방법 3: 키보드 이벤트 시뮬레이션
    if not success:
        try:
            print("방법 3: 키보드 이벤트로 텍스트 입력 시도...")
            driver.execute_script("""
                var element = arguments[0];
                var text = arguments[1];
                element.focus();
                element.innerHTML = '';

                // 텍스트 입력 이벤트 시뮬레이션
                var inputEvent = new Event('input', { bubbles: true });
                element.textContent = text;
                element.dispatchEvent(inputEvent);

                // 변경 이벤트도 트리거
                var changeEvent = new Event('change', { bubbles: true });
                element.dispatchEvent(changeEvent);
            """, editor, final_text)
            success = True
            print("키보드 이벤트 시뮬레이션으로 텍스트 입력 성공!")
        except Exception as e:
            print(f"키보드 이벤트 시뮬레이션 실패: {e}")

    if not success:
        print("모든 텍스트 입력 방법이 실패했습니다.")
        return False

    # 8) 입력된 내용 확인
    try:
        current_text = editor.get_attribute('textContent') or editor.text
        print(f"입력된 텍스트 확인: '{current_text}'")
    except Exception as e:
        print(f"텍스트 확인 실패: {e}")

    # 9) 등록 버튼 찾기
    try:
        print("등록 버튼 찾기...")
        submit_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.u_cbox_btn_upload.__uis_naverComment_writeButton")))
        print("등록 버튼을 찾았습니다.")
    except Exception as e:
        print(f"기본 등록 버튼 찾기 실패: {e}")
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[data-action='write#request']")
            print("대체 등록 버튼을 찾았습니다.")
        except Exception as e2:
            print(f"대체 등록 버튼 찾기도 실패: {e2}")
            return False

    # 10) 등록 버튼 클릭
    try:
        print("등록 버튼 클릭...")
        submit_btn.click()
        time.sleep(3)  # 등록 처리 대기
        print("등록 버튼 클릭 성공!")
    except Exception as e:
        print(f"일반 클릭 실패: {e}")
        try:
            print("JavaScript로 등록 버튼 클릭 시도...")
            driver.execute_script("arguments[0].click();", submit_btn)
            time.sleep(3)
            print("JavaScript 클릭 성공!")
        except Exception as e2:
            print(f"JavaScript 클릭도 실패: {e2}")
            return False

    # 11) iframe에서 나가기 (필요시)
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    print("=== 댓글 작성 완료 ===")
    return True


def add_context_menu(entry):
    menu = tk.Menu(entry, tearoff=0)
    menu.add_command(label="복사", command=lambda: entry.event_generate("<<Copy>>"))
    menu.add_command(label="붙여넣기", command=lambda: entry.event_generate("<<Paste>>"))

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    entry.bind("<Button-3>", show_menu)


if __name__ == '__main__':
    global root
    root = tk.Tk()
    root.title("네이버 자동 머신")

    tk.Label(root, text="네이버 아이디:").grid(row=0, column=0, padx=10, pady=10)
    entry_id = tk.Entry(root, width=30)
    entry_id.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(root, text="네이버 비밀번호:").grid(row=1, column=0, padx=10, pady=10)
    entry_pw = tk.Entry(root, show="*", width=30)
    entry_pw.grid(row=1, column=1, padx=10, pady=10)

    login_btn = tk.Button(root, text="로그인", command=login_button_click)
    login_btn.grid(row=2, column=0, padx=10, pady=20)

    login_complete_btn = tk.Button(root, text="로그인 완료", command=login_complete_button_click)
    login_complete_btn.grid(row=2, column=1, padx=10, pady=20)

    label_info = tk.Label(root, text="아이디와 비밀번호를 입력하고 로그인하세요.")
    label_info.grid(row=4, column=0, columnspan=2, pady=10)

    btn_neighbor_blog = tk.Button(root, text="블로그 확인", command=btn_neighbor_blog_click)
    btn_neighbor_blog.grid_remove()

    root.mainloop()