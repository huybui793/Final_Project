import streamlit as st
from database.database import get_topic_stats
from core.ytb_process import search_youtube_videos

WEAK_THRESHOLD = 0.6  # dưới 60% đúng thì coi là chủ đề yếu


def _level(rate):
    if rate < WEAK_THRESHOLD:
        return "🔴 Cần ôn lại"
    if rate < 0.8:
        return "🟡 Tạm ổn"
    return "🟢 Vững"


def _summarize_attempt(results_detail):
    stats = {}
    for r in results_detail:
        topic = r.get("topic") or "Khác"
        s = stats.setdefault(topic, {"total": 0, "correct": 0})
        s["total"] += 1
        s["correct"] += 1 if r["is_correct"] else 0
    return stats


def _render_topic_rows(stats):
    # Chủ đề yếu nhất hiện lên đầu
    rows = sorted(stats.items(), key=lambda kv: kv[1]["correct"] / kv[1]["total"])
    for topic, s in rows:
        rate = s["correct"] / s["total"]
        st.write(f"**{topic}**: {s['correct']}/{s['total']} câu đúng ({round(rate * 100)}%) · {_level(rate)}")
        st.progress(rate)


def render_exam_report(results_detail, user_id):
    st.divider()
    st.subheader("📊 Báo cáo năng lực theo chủ đề")

    # --- Bài vừa làm ---
    attempt = _summarize_attempt(results_detail)
    st.markdown("**Bài kiểm tra vừa làm**")
    _render_topic_rows(attempt)

    weak_now = [t for t, s in attempt.items() if s["correct"] / s["total"] < WEAK_THRESHOLD]
    if weak_now:
        st.warning("Cần ôn lại: " + ", ".join(weak_now))
    else:
        st.success("Bạn nắm vững tất cả chủ đề trong bài này.")

    # --- Tổng hợp mọi bài đã làm ---
    history = get_topic_stats(user_id)
    if history:
        st.markdown("**Tổng hợp tất cả các bài đã làm**")
        _render_topic_rows({
            h["topic"]: {"total": h["total"], "correct": h["correct"]} for h in history
        })

    # --- Gợi ý video ôn tập (chỉ gọi khi bấm nút, kết quả được giữ lại) ---
    if weak_now:
        if st.button("▶️ Gợi ý video ôn tập", key="report_videos_btn"):
            videos = {}
            for topic in weak_now[:3]:  # giới hạn 3 chủ đề để tiết kiệm quota YouTube
                try:
                    videos[topic] = search_youtube_videos(f"{topic} lịch sử", max_results=2)
                except Exception:
                    videos[topic] = []
            st.session_state.report_videos = videos

        for topic, vids in st.session_state.get("report_videos", {}).items():
            st.markdown(f"**{topic}**")
            if not vids:
                st.caption("Không tìm được video cho chủ đề này.")
            for v in vids:
                st.video(v["url"])
                st.caption(v["title"])