// frontend/pages/index.tsx
import ChatPage from "./ChatPage";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">
          🤖 RAG Chat Bot
        </h1>
        <ChatPage />
      </div>
    </div>
  );
}
