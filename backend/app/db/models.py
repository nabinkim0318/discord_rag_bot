# # backend/app/db/models.py
# -- messages (user_messages)
# CREATE TABLE IF NOT EXISTS user_messages (
#   id UUID PRIMARY KEY,
#   user_id TEXT NOT NULL,              -- Discord user id
#   channel_id TEXT NOT NULL,           -- Discord channel id
#   question TEXT NOT NULL,
#   response TEXT,                      -- 최종 응답 텍스트
#   discord_message_id TEXT,            -- 봇이 채널에 보낸 메시지 id (피드백 연결 시 유용)
#   private BOOLEAN DEFAULT FALSE,      -- DM로 보냈는지 여부
#   latency_ms INTEGER,                 -- RAG 왕복 시간
#   status TEXT CHECK (status IN ('success','error')) DEFAULT 'success',
#   error TEXT,
#   created_at TIMESTAMP DEFAULT NOW()
# );

# CREATE INDEX IF NOT EXISTS idx_user_messages_discord_msg_id
#   ON user_messages(discord_message_id);

# -- feedback
# CREATE TABLE IF NOT EXISTS feedback (
#   id UUID PRIMARY KEY,
#   message_id UUID NOT NULL REFERENCES user_messages(id) ON DELETE CASCADE,
#   user_id TEXT NOT NULL,
#   score TEXT CHECK (score IN ('up','down')) NOT NULL,
#   comment TEXT,
#   created_at TIMESTAMP DEFAULT NOW()
# );

# CREATE INDEX IF NOT EXISTS idx_feedback_message_id
#   ON feedback(message_id);

# -- metrics_log (선택: 원시 로그용, 프로메테우스 지표와 병행)
# CREATE TABLE IF NOT EXISTS metrics_log (
#   id UUID PRIMARY KEY,
#   type TEXT,                            -- 'rag_query','health_check' 등
#   status TEXT,
#   latency_seconds DOUBLE PRECISION,
#   timestamp TIMESTAMP DEFAULT NOW()
# );
