import sys
import time
import requests
import pyotp

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE_URL = "http://localhost:5000"

def run_tests():
    print("\n=======================================================")
    print("   AI NEWS LETTER — COMPREHENSIVE AUTOMATED TEST SUITE   ")
    print("=======================================================\n")

    session = requests.Session()
    session_id = f"test_session_{int(time.time())}"
    headers = {"X-Session-ID": session_id}

    # 1. HTML Pages
    print("[TEST 1] Verifying Frontend Pages...")
    for path in ["/", "/home.html", "/article.html"]:
        r = session.get(f"{BASE_URL}{path}")
        assert r.status_code == 200, f"Page {path} failed with {r.status_code}"
        assert "AI NEWS" in r.text, f"Page {path} missing brand text"
    print(" -> PASS: Start page, Home page, and Article page loaded successfully.")

    # 2. News Feed - Exactly 21 cards
    print("\n[TEST 2] Verifying News Feed (Exactly 21 Cards, All Unique)...")
    r = session.get(f"{BASE_URL}/api/news?category=All", headers=headers)
    assert r.status_code == 200, f"News fetch failed: {r.text}"
    data = r.json()
    articles_1 = data.get("articles", [])
    print(f" -> Received {len(articles_1)} articles.")
    assert len(articles_1) == 21, f"Expected 21 articles, got {len(articles_1)}"
    
    urls_1 = [a["url"] for a in articles_1]
    assert len(urls_1) == len(set(urls_1)), "Duplicates found within single feed screen!"
    print(" -> PASS: Exactly 21 unique articles returned.")

    # 3. No-Repeat Rule & Refresh
    print("\n[TEST 3] Verifying No-Repeat Logic on Refresh...")
    r = session.get(f"{BASE_URL}/api/news?category=All&refresh=true", headers=headers)
    assert r.status_code == 200
    data = r.json()
    articles_2 = data.get("articles", [])
    print(f" -> Received {len(articles_2)} fresh articles on refresh.")
    assert len(articles_2) == 21, f"Expected 21 articles, got {len(articles_2)}"
    urls_2 = [a["url"] for a in articles_2]
    assert len(urls_2) == len(set(urls_2)), "Duplicates found within refreshed screen!"

    # Check intersection between run 1 and run 2
    overlap = set(urls_1) & set(urls_2)
    print(f" -> Overlap between load 1 and load 2: {len(overlap)} articles (Goal: 0).")
    assert len(overlap) == 0, f"Articles repeated across refreshes! Repeated: {overlap}"
    print(" -> PASS: Refresh returned 21 completely NEW, non-repeating articles.")

    # 4. All 7 Categories
    print("\n[TEST 4] Verifying all 7 Categories...")
    cats = ["Technology", "AI", "Science", "Startups", "Business", "Cyber Security", "World News"]
    for c in cats:
        r = session.get(f"{BASE_URL}/api/news?category={requests.utils.quote(c)}", headers={"X-Session-ID": f"cat_test_{c}_{int(time.time())}"})
        assert r.status_code == 200, f"Category {c} failed"
        c_arts = r.json().get("articles", [])
        assert len(c_arts) == 21, f"Category {c} expected 21 articles, got {len(c_arts)}"
        # Verify category tag
        for a in c_arts:
            assert a["category"] == c, f"Article category mismatch: {a['category']} != {c}"
        print(f"   [OK] {c}: 21 articles fetched successfully.")
    print(" -> PASS: All 7 categories verified.")

    # 5. Search
    print("\n[TEST 5] Verifying Search functionality...")
    r = session.get(f"{BASE_URL}/api/news/search?q=Intelligence")
    assert r.status_code == 200
    results = r.json().get("articles", [])
    assert len(results) > 0, "No search results returned for 'Intelligence'"
    print(f" -> PASS: Search returned {len(results)} relevant articles.")

    # 6. Strict Authentication: Signup vs Login & OTP Lifecycle
    print("\n[TEST 6] Verifying Authentication & OTP Lifecycle...")
    test_email = f"tester_{int(time.time())}@ainewsletter.test"
    test_phone = f"+9198{int(time.time()) % 100000000:08d}"

    # A. Unregistered user tries to LOGIN -> Should Fail with 404
    r = session.post(f"{BASE_URL}/api/auth/send-otp", json={
        "type": "email",
        "identifier": test_email,
        "purpose": "login"
    })
    assert r.status_code == 404, f"Expected 404 for login with unregistered user, got {r.status_code}"
    assert "Account not found" in r.json().get("message", "")
    print("   ✓ Unregistered user login blocked ('Account not found, please sign up').")

    # B. User SIGNUP with Email
    r = session.post(f"{BASE_URL}/api/auth/send-otp", json={
        "type": "email",
        "identifier": test_email,
        "purpose": "signup"
    })
    assert r.status_code == 200, f"Email OTP request failed: {r.text}"
    otp_data = r.json()
    assert "dev_otp" in otp_data, "dev_otp expected in dev mode"
    email_otp = otp_data["dev_otp"]
    print(f"   ✓ Email OTP received: {email_otp}")

    # C. Verify OTP with wrong code -> Should Fail
    r = session.post(f"{BASE_URL}/api/auth/verify-otp", json={
        "type": "email",
        "identifier": test_email,
        "otp": "000000",
        "purpose": "signup"
    })
    assert r.status_code == 400, "Wrong OTP should fail with 400"
    print("   ✓ Invalid OTP rejected.")

    # D. Verify OTP with correct code
    r = session.post(f"{BASE_URL}/api/auth/verify-otp", json={
        "type": "email",
        "identifier": test_email,
        "otp": email_otp,
        "purpose": "signup"
    })
    assert r.status_code == 200, f"Valid OTP verification failed: {r.text}"
    auth_data = r.json()
    user_token = auth_data["token"]
    user_id = auth_data["user"]["id"]
    print("   ✓ Email verified & user registered successfully.")

    # E. Test Persistent Session /me
    r = session.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    assert r.json().get("authenticated") is True
    print("   ✓ Persistent JWT validated via /api/auth/me.")

    # F. Phone Signup
    r = session.post(f"{BASE_URL}/api/auth/send-otp", json={
        "type": "phone",
        "identifier": test_phone,
        "purpose": "signup"
    })
    assert r.status_code == 200, f"Phone OTP request failed: {r.text}"
    phone_otp = r.json().get("dev_otp")
    print(f"   ✓ Phone OTP received: {phone_otp}")

    r = session.post(f"{BASE_URL}/api/auth/verify-otp", json={
        "type": "phone",
        "identifier": test_phone,
        "otp": phone_otp,
        "purpose": "signup"
    })
    assert r.status_code == 200, f"Phone OTP verification failed: {r.text}"
    print("   ✓ Phone (+919876543210) verified & registered successfully.")

    # 7. Saved Articles (Bookmark)
    print("\n[TEST 7] Verifying Saved News (Bookmark) Operations...")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    sample_art = articles_1[0]

    # Save article
    r = session.post(f"{BASE_URL}/api/news/save", json={
        "url": sample_art["url"],
        "title": sample_art["title"],
        "description": sample_art.get("description", ""),
        "image": sample_art.get("image", ""),
        "source": sample_art.get("source", "News"),
        "published_at": sample_art.get("published_at", ""),
        "category": sample_art.get("category", "AI"),
        "action": "save"
    }, headers=user_headers)
    assert r.status_code == 200
    assert r.json().get("saved") is True
    print("   ✓ Article saved successfully.")

    # Fetch saved articles
    r = session.get(f"{BASE_URL}/api/news/saved", headers=user_headers)
    assert r.status_code == 200
    saved_list = r.json().get("articles", [])
    assert len(saved_list) >= 1
    assert any(a["url"] == sample_art["url"] for a in saved_list)
    print("   ✓ Saved article retrieved from /api/news/saved.")

    # Unsave article
    r = session.post(f"{BASE_URL}/api/news/save", json={
        "url": sample_art["url"],
        "action": "unsave"
    }, headers=user_headers)
    assert r.status_code == 200
    assert r.json().get("saved") is False
    print("   ✓ Article unsaved successfully.")

    # 8. Summarizer
    print("\n[TEST 8] Verifying AI News Summarizer...")
    long_article_text = (
        "Researchers at leading artificial intelligence institutions announced a groundbreaking architecture "
        "for autonomous agent coordination today. The new paradigm enables multi-agent models to self-organize, "
        "verify algorithmic outputs, and execute complex workflows with dramatically lower latency and error rates. "
        "In industry benchmarks, the framework achieved a 42 percent reduction in hallucination rates across scientific domains. "
        "Enterprise technology executives highlighted the potential for substantial cost reductions in cloud infrastructure. "
        "Global cybersecurity teams also noted that cryptographic verification protocols built into the models ensure data integrity. "
        "The open-weights implementation has been released to the global developer community for collaborative validation and scaling."
    )
    r = session.post(f"{BASE_URL}/api/summarize", json={"text": long_article_text})
    assert r.status_code == 200, f"Summarizer failed: {r.text}"
    summary_res = r.json().get("summary", {})
    assert "headline" in summary_res
    assert "bullets" in summary_res
    assert len(summary_res["bullets"]) >= 5
    assert "paragraph" in summary_res
    print(f"   ✓ Summary synthesized: Headline: '{summary_res['headline']}'")
    print(f"   ✓ Bullet points count: {len(summary_res['bullets'])}")
    print(" -> PASS: Summarizer returned headline, 5-7 key bullets, and paragraph.")

    # 9. Article Page & Visitor Logging
    print("\n[TEST 9] Verifying Article Page & Visit Logging...")
    art_id = sample_art.get("id")
    if art_id:
        r = session.get(f"{BASE_URL}/api/news/article/{art_id}")
        assert r.status_code == 200
        art_detail = r.json().get("article", {})
        assert "ai_summary" in art_detail
        print("   ✓ Article detail returned with AI summary.")

    # Log visit
    r = session.post(f"{BASE_URL}/api/news/log-visit", json={
        "title": sample_art["title"],
        "url": sample_art["url"],
        "category": sample_art["category"]
    }, headers=user_headers)
    assert r.status_code == 200
    print("   ✓ User activity logged.")

    # 10. Administrator Section & 2FA TOTP
    print("\n[TEST 10] Verifying Administrator 2FA Portal & Dashboard...")
    # Step 1: Admin credentials
    r = session.post(f"{BASE_URL}/api/admin/login", json={
        "admin_id": "admin",
        "password": "Admin@12345"
    })
    assert r.status_code == 200, f"Admin login step 1 failed: {r.text}"
    admin_login_res = r.json()
    assert admin_login_res.get("require_2fa") is True
    temp_admin_token = admin_login_res.get("temp_token")
    print("   ✓ Step 1: Admin ID & Password verified. 2FA required.")

    # Step 2: 2FA TOTP verification
    totp = pyotp.TOTP("VMVN5V3QCWYR43SSYUXGLIZUV2IMPUVG")
    live_code = totp.now()
    print(f"   ✓ Generated live TOTP code: {live_code}")

    r = session.post(f"{BASE_URL}/api/admin/verify-2fa", json={
        "temp_token": temp_admin_token,
        "totp_code": live_code
    })
    assert r.status_code == 200, f"Admin 2FA failed: {r.text}"
    admin_token = r.json().get("admin_token")
    print("   ✓ Step 2: 2FA TOTP code verified. Admin session granted.")

    # Test Admin Dashboard: Registered Users
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    r = session.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
    assert r.status_code == 200, f"Admin users failed: {r.text}"
    users_list = r.json().get("users", [])
    print(f"   ✓ Admin Dashboard loaded {len(users_list)} registered users.")
    assert len(users_list) >= 2, "Expected at least 2 users (email + phone)"

    # Test Admin Dashboard: Activity Logs with Search
    r = session.get(f"{BASE_URL}/api/admin/activity?q=", headers=admin_headers)
    assert r.status_code == 200, f"Admin activity failed: {r.text}"
    activity_logs = r.json().get("activity", [])
    print(f"   ✓ Admin Dashboard loaded {len(activity_logs)} activity log entries.")
    assert len(activity_logs) >= 1, "Expected at least 1 activity record"

    # Test Unauthorized user access blocked
    r = requests.get(f"{BASE_URL}/api/admin/users", headers=user_headers)
    assert r.status_code == 403, "Non-admin user must receive 403 Forbidden"
    print("   ✓ Non-admin access to admin API successfully blocked with 403 Forbidden.")

    print("\n=======================================================")
    print("   🎉 ALL 10 TEST SUITES PASSED FLAWLESSLY (100%)    ")
    print("=======================================================\n")

if __name__ == "__main__":
    run_tests()
