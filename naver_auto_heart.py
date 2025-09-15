import tkinter as tk
from time import sleep
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver import ActionChains
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
LOGIN_DATA_FILE = "login_data.json"
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

def save_login_data(user_id, user_pw):
    data = {"user_id": user_id, "user_pw": user_pw}
    with open(LOGIN_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_login_data():
    if os.path.exists(LOGIN_DATA_FILE):
        with open(LOGIN_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("user_id", None), data.get("user_pw", None)
    return None, None


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

    save_login_data(user_id, user_pw)

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


def neighborNewFeed(max_pages=50):
    base_url = "https://section.blog.naver.com/BlogHome.naver?directoryNo=0¤tPage={}&groupId=0"
    current_page = 1
    total_liked_count = 0  # 전체 공감 완료 개수 추적

    while current_page <= max_pages:
        driver.get(base_url.format(current_page))
        # 올바른 셀렉터로 수정
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[ng-repeat*='buddyPostList']"))
        )
        time.sleep(2)

        print(f"=== {current_page} 페이지 처리 시작 ===")

        # 올바른 셀렉터로 수정
        posts = driver.find_elements(By.CSS_SELECTOR, "div[ng-repeat*='buddyPostList']")
        print(f"실제 찾은 글 개수: {len(posts)}")

        stop_flag = False
        processed_count = 0

        for idx, post in enumerate(posts, start=1):
            print(f"=== {idx}번째 글 처리 시작 (processed_count: {processed_count}) ===")
            if processed_count >= 10:
                print("10개 처리 완료로 break")
                break

            try:
                # 좋아요 버튼 상태 확인
                like_btn = post.find_element(By.CSS_SELECTOR, "a.u_likeit_button._face")
                pressed = like_btn.get_attribute("aria-pressed")

                if pressed == "true":
                    print(f"[{current_page}페이지 {idx}번째] 이미 눌린 글 발견 → 전체 종료")
                    stop_flag = True
                    break

                # 아이콘 클릭해서 레이어 열기
                icons_btn = post.find_element(By.CSS_SELECTOR, "span.u_likeit_icons._icons")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", icons_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", icons_btn)
                print(f"[{current_page}페이지 {idx}번째] 공감 아이콘 클릭하여 레이어 열기")

                # 나머지 코드는 동일...
                # 레이어가 열릴 때까지 대기
                WebDriverWait(post, 5).until(
                    lambda p: "display: block" in p.find_element(
                        By.CSS_SELECTOR, "ul.u_likeit_layer._faceLayer"
                    ).get_attribute("style")
                )

                # 가능한 버튼 모으기
                reaction_buttons = []
                for selector, rtype in [
                    ("li.u_likeit_list.like a", "like"),
                    ("li.u_likeit_list.impressive a", "impressive"),
                    ("li.u_likeit_list.thanks a", "thanks")
                ]:
                    try:
                        btn = post.find_element(By.CSS_SELECTOR, selector)
                        reaction_buttons.append((rtype, btn))
                    except:
                        pass

                if reaction_buttons:
                    # 랜덤 클릭
                    reaction_type, target_button = random.choice(reaction_buttons)
                    driver.execute_script("arguments[0].click();", target_button)
                    print(f"[{current_page}페이지 {idx}번째] 공감 클릭 성공 → {reaction_type}")
                    total_liked_count += 1  # 공감 성공 시 카운트 증가

                    # 대기
                    sleep_time = random.randint(3, 5)
                    print(f"  → {sleep_time}초 대기...")
                    time.sleep(sleep_time)
                else:
                    print(f"[{current_page}페이지 {idx}번째] 공감 버튼 없음 (카운트만 증가)")

                # 버튼 있든 없든 처리한 글 카운트 증가
                processed_count += 1

            except Exception as e:
                print(f"[{current_page}페이지 {idx}번째] 처리 실패: {e}")
                # 실패해도 글 하나는 처리한 것으로 카운트
                processed_count += 1
                continue

        print(f"[{current_page}페이지] 총 {processed_count}개 처리 완료 (공감 성공: {total_liked_count}개)")

        if stop_flag:
            print("이미 공감한 글 발견으로 종료")
            break

        # 다음 페이지 이동
        current_page += 1
        if current_page <= max_pages:
            sleep_time = random.randint(10, 15)
            print(f"=== 다음 페이지({current_page})로 이동 전 {sleep_time}초 대기 ===")
            time.sleep(sleep_time)
        else:
            print("최대 페이지 수에 도달하여 종료")
            break

    print(f"neighborNewFeed 종료 - 총 {total_liked_count}개 글에 공감 완료")
    return total_liked_count  # 총 공감 개수 반환


def debug_selectors():
    driver.get("https://section.blog.naver.com/BlogHome.naver?directoryNo=0&currentPage=1&groupId=0")
    time.sleep(5)  # 충분한 로딩 시간

    # 다양한 셀렉터들 시도
    selectors_to_try = [
        "div.item_multi_pic",
        "div.list_post_article",
        "div[ng-repeat*='post']",
        "div[ng-repeat*='buddyPostList']",
        ".item_multi_pic",
        "[ng-repeat]",
        "div[class*='item']",
        "div[class*='post']"
    ]

    for selector in selectors_to_try:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"셀렉터 '{selector}': {len(elements)}개 발견")
            if elements and len(elements) > 0:
                print(f"  첫 번째 요소의 클래스: {elements[0].get_attribute('class')}")
                print(f"  첫 번째 요소의 HTML (앞 200자): {elements[0].get_attribute('outerHTML')[:200]}...")
        except Exception as e:
            print(f"셀렉터 '{selector}': 에러 - {e}")


def btn_neighbor_blog_click():
    global driver
    if not driver:
        messagebox.showwarning("경고", "먼저 로그인 해주세요.")
        return

    scroll_time = default_scroll_time

    progress_win = tk.Toplevel(root)
    progress_win.title("진행 중...")
    progress_label = tk.Label(progress_win, text="공감 중...")
    progress_label.pack(padx=20, pady=5)
    progress_bar = ttk.Progressbar(progress_win, mode='determinate', length=300)
    progress_bar.pack(padx=20, pady=20)

    def task():
        total_liked_count = 0
        try:
            total_liked_count = neighborNewFeed()
        finally:
            # progress 창 닫기
            progress_win.destroy()
            # 완료 알림 띄우기
            messagebox.showinfo("완료", f"총 {total_liked_count}개의 글에 공감을 완료했습니다!")

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

                # # 2) 댓글 작성 (체크박스가 활성화된 경우에만)
                # comment_success = False
                # if use_comments and like_success:
                #     comment_success = process_comment(driver, url, comment_texts)
                #
                # if like_success or comment_success:
                #     success_count += 1
                #     print(f"블로그 처리 완료 - 공감: {like_success}, 댓글: {comment_success}")
                # else:
                #     print("블로그 처리 실패")
                #
                # # 다음 블로그 처리 전 대기
                # time.sleep(random.randint(5, 10))

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

    def click_like_button_original(driver, url):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.randint(3, 6))

            # 1) 여러 방법으로 공감 버튼 클릭 시도
            like_clicked = False

            # 방법 1: 직접 클릭
            try:
                like_area = driver.find_element(By.CSS_SELECTOR, "span.u_likeit_icons._icons")
                ActionChains(driver).move_to_element(like_area).click().perform()
                like_clicked = True
                print("공감 버튼 클릭 성공 (ActionChains)")
            except Exception as e:
                print(f"ActionChains 클릭 실패: {e}")

            # 방법 2: JavaScript 클릭 (방법 1이 실패한 경우)
            if not like_clicked:
                try:
                    like_area = driver.find_element(By.CSS_SELECTOR, "span.u_likeit_icons._icons")
                    driver.execute_script("arguments[0].click();", like_area)
                    like_clicked = True
                    print("공감 버튼 클릭 성공 (JS 클릭)")
                except Exception as e:
                    print(f"JS 클릭 실패: {e}")

            # 방법 3: 마우스 이벤트 직접 발생
            if not like_clicked:
                try:
                    like_area = driver.find_element(By.CSS_SELECTOR, "span.u_likeit_icons._icons")
                    driver.execute_script("""
                        var element = arguments[0];
                        var rect = element.getBoundingClientRect();
                        var event = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: rect.left + rect.width/2,
                            clientY: rect.top + rect.height/2
                        });
                        element.dispatchEvent(event);
                    """, like_area)
                    like_clicked = True
                    print("공감 버튼 클릭 성공 (마우스 이벤트)")
                except Exception as e:
                    print(f"마우스 이벤트 실패: {e}")

            if not like_clicked:
                print("모든 클릭 방법 실패")
                return False

            # 2) 레이어가 열릴 때까지 더 유연하게 대기
            time.sleep(1)  # 짧은 대기

            # 레이어 상태 확인을 위한 여러 방법
            layer_opened = False

            # 방법 1: display 스타일 확인
            try:
                layer = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.u_likeit_layer_faceLayer"))
                )
                style = layer.get_attribute("style")
                if "display: block" in style or "display:block" in style:
                    layer_opened = True
                    print("레이어 열림 확인 (display: block)")
            except:
                pass

            # 방법 2: 가시성 확인
            if not layer_opened:
                try:
                    layer = driver.find_element(By.CSS_SELECTOR, "ul.u_likeit_layer_faceLayer")
                    if layer.is_displayed():
                        layer_opened = True
                        print("레이어 열림 확인 (is_displayed)")
                except:
                    pass

            # 방법 3: 자식 요소들이 보이는지 확인
            if not layer_opened:
                try:
                    reaction_buttons = WebDriverWait(driver, 3).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "ul.u_likeit_layer_faceLayer li.u_likeit_list a"))
                    )
                    if len(reaction_buttons) > 0 and reaction_buttons[0].is_displayed():
                        layer_opened = True
                        print("레이어 열림 확인 (버튼 가시성)")
                except:
                    pass

            if not layer_opened:
                print("공감 레이어가 열리지 않음")
                # 디버깅: 현재 레이어 상태 출력
                try:
                    layer = driver.find_element(By.CSS_SELECTOR, "ul.u_likeit_layer_faceLayer")
                    print(f"레이어 스타일: {layer.get_attribute('style')}")
                    print(f"레이어 표시 상태: {layer.is_displayed()}")
                except Exception as e:
                    print(f"레이어 상태 확인 실패: {e}")
                return False

            # 3) 공감 버튼들 찾기 및 클릭
            try:
                reaction_buttons = driver.find_elements(
                    By.CSS_SELECTOR, "ul.u_likeit_layer_faceLayer li.u_likeit_list a"
                )

                if not reaction_buttons:
                    print("공감 버튼들을 찾을 수 없음")
                    return False

                # 상위 3개 버튼 중 랜덤 선택
                available_buttons = [btn for btn in reaction_buttons[:3] if btn.is_displayed()]

                if not available_buttons:
                    print("표시된 공감 버튼이 없음")
                    return False

                target = random.choice(available_buttons)

                # 버튼 클릭 시도
                try:
                    ActionChains(driver).move_to_element(target).click().perform()
                    print("공감 표현 성공 (ActionChains):", target.get_attribute("data-type") or target.get_attribute("role"))
                except:
                    driver.execute_script("arguments[0].click();", target)
                    print("공감 표현 성공 (JS):", target.get_attribute("data-type") or target.get_attribute("role"))

                time.sleep(1)  # 클릭 후 짧은 대기
                return True

            except Exception as e:
                print(f"공감 버튼 클릭 오류: {e}")
                return False

        except Exception as e:
            print(f"전체 공감 처리 오류: {e}")
            return False


def reset_to_login_ui():
    """모든 위젯 파괴 후 초기 로그인 UI 복원, show_post_login_ui 호출"""

    # 1. 기존 위젯 모두 파괴
    for widget in root.winfo_children():
        widget.destroy()

    btn_neighbor_blog = tk.Button(root, text="공감 시작", command=btn_neighbor_blog_click)
    btn_neighbor_blog.grid(row=3, column=0, padx=10, pady=10)




# 추가: 디버깅용 함수
def debug_like_button_state(driver):
    """현재 좋아요 버튼 상태를 디버깅하는 함수"""
    try:
        # 공감 아이콘 상태 확인
        like_icon = driver.find_element(By.CSS_SELECTOR, "span.u_likeit_icons._icons")
        print(f"공감 아이콘 표시 상태: {like_icon.is_displayed()}")
        print(f"공감 아이콘 클래스: {like_icon.get_attribute('class')}")

        # 레이어 상태 확인
        try:
            layer = driver.find_element(By.CSS_SELECTOR, "ul.u_likeit_layer_faceLayer")
            print(f"레이어 스타일: {layer.get_attribute('style')}")
            print(f"레이어 표시 상태: {layer.is_displayed()}")

            # 버튼들 상태 확인
            buttons = driver.find_elements(By.CSS_SELECTOR, "ul.u_likeit_layer_faceLayer li.u_likeit_list a")
            print(f"찾은 버튼 개수: {len(buttons)}")
            for i, btn in enumerate(buttons[:3]):
                print(f"버튼 {i + 1} - 표시상태: {btn.is_displayed()}, role: {btn.get_attribute('role')}")
        except Exception as e:
            print(f"레이어 상태 확인 실패: {e}")

    except Exception as e:
        print(f"디버깅 실패: {e}")


# 사용 예시
# debug_like_button_state(driver)  # 문제 상황에서 호출하여 상태 확인
# result = click_like_button_improved(driver, url)





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

    user_id, user_pw = load_login_data()

    tk.Label(root, text="네이버 아이디:").grid(row=0, column=0, padx=10, pady=10)
    entry_id = tk.Entry(root, width=30)
    entry_id.grid(row=0, column=1, padx=10, pady=10)
    if user_id:
        entry_id.insert(0, user_id)

    tk.Label(root, text="네이버 비밀번호:").grid(row=1, column=0, padx=10, pady=10)
    entry_pw = tk.Entry(root, show="*", width=30)
    entry_pw.grid(row=1, column=1, padx=10, pady=10)
    if user_pw:
        entry_pw.insert(0, user_pw)

    login_btn = tk.Button(root, text="로그인", command=login_button_click)
    login_btn.grid(row=2, column=0, padx=10, pady=20)

    login_complete_btn = tk.Button(root, text="로그인 완료", command=login_complete_button_click)
    login_complete_btn.grid(row=2, column=1, padx=10, pady=20)

    label_info = tk.Label(root, text="아이디와 비밀번호를 입력하고 로그인하세요.")
    label_info.grid(row=4, column=0, columnspan=2, pady=10)

    btn_neighbor_blog = tk.Button(root, text="공감 시작", command=btn_neighbor_blog_click)
    btn_neighbor_blog.grid_remove()

    root.mainloop()
