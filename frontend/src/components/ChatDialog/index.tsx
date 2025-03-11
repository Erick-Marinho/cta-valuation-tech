import axios from 'axios';
import { useEffect, useRef, useState } from 'react';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface ChatDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

// Interface para a resposta da API
interface ApiResponse {
  response: string;
}

const ChatDialog = ({ isOpen, onClose }: ChatDialogProps) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Olá! Sou o Assistente CTA, especialista em valoração de tecnologias relacionadas ao Patrimônio Genético Nacional e Conhecimentos Tradicionais Associados. Como posso ajudar você hoje?',
      sender: 'assistant',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-foco no input quando o chat é aberto
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [isOpen]);

  // Auto-scroll para a última mensagem quando novas mensagens são adicionadas
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Função para rolar até o final
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit'
    });
  };

  // Alterna entre modo expandido e compacto
  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  // Função para fazer requisição à API RAG
  const fetchRagResponse = async (query: string): Promise<string> => {
    try {
      // Configurando headers específicos para evitar problemas de CORS
      const config = {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      };
      
      const response = await axios.post<ApiResponse>('http://localhost:8000/chat', {
        query: query
      }, config);
      
      return response.data.response;
    } catch (error) {
      console.error('Erro ao consultar a API RAG:', error);
      return 'Desculpe, não consegui processar sua solicitação. Ocorreu um erro de comunicação com o servidor.';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (input.trim() === '') return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      text: input,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    try {
      // Obtém resposta do sistema RAG
      const ragResponse = await fetchRagResponse(input);
      
      const assistantMessage: Message = {
        id: Date.now().toString(),
        text: ragResponse,
        sender: 'assistant',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Erro ao processar a consulta:', error);
      
      const errorMessage: Message = {
        id: Date.now().toString(),
        text: 'Desculpe, ocorreu um erro ao buscar as informações. Por favor, tente novamente mais tarde.',
        sender: 'assistant',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  // Definindo os estilos baseados no estado atual
  const containerStyles = isExpanded
    ? "fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    : "fixed bottom-6 right-6 z-50";

  const chatStyles = isExpanded
    ? "w-4/5 h-4/5 md:w-3/4 md:h-3/4"
    : "w-full md:w-96 h-[500px]";

  return (
    <div className={containerStyles}>
      {/* Estilos para a barra de rolagem personalizada */}
      <style jsx global>{`
        /* Estilo para barra de rolagem em navegadores WebKit */
        .custom-scrollbar::-webkit-scrollbar {
          width: 5px;
        }
        
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: rgba(203, 213, 225, 0.4);
          border-radius: 20px;
          border: transparent;
        }
        
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background-color: rgba(148, 163, 184, 0.6);
        }
        
        /* Estilo para Firefox */
        .custom-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: rgba(203, 213, 225, 0.4) transparent;
        }
      `}</style>
      
      {/* Caixa de diálogo */}
      <div className={`${chatStyles} flex flex-col bg-white shadow-xl rounded-lg border border-[#f59e0b]/30 overflow-hidden transition-none`}>
        {/* Header controls */}
        <div className="flex items-center justify-between py-3 px-4 border-b border-gray-200 bg-gradient-to-r from-[#f59e0b]/90 to-[#10b981]/90">
          <h3 className="text-white font-semibold">Assistente CTA Value Tech</h3>
          <div className="flex items-center space-x-3">
            <button 
              onClick={toggleExpand} 
              className="text-white hover:text-gray-100"
              aria-label={isExpanded ? "Minimizar chat" : "Expandir chat"}
            >
              {isExpanded ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 3h6v6M14 10l6.1-6.1M9 21H3v-6M10 14l-6.1 6.1"></path>
                </svg>
              )}
            </button>
            <button 
              onClick={onClose}
              className="text-white hover:text-gray-100"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>
        
        {/* Title */}
        <div className="px-4 py-4 text-center">
          <h2 className="text-2xl font-bold text-[#0b2e6e]">Assistente <span className="text-[#f59e0b]">CTA Value Tech</span></h2>
          <p className="text-sm text-gray-600 mt-1">Consulte informações sobre valoração de tecnologias, repartição de benefícios e biodiversidade - {formatTime(new Date())}</p>
        </div>
        
        {/* Messages container com barra de rolagem suave */}
        <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-2">
          {messages.map((message) => (
            <div key={message.id} className={`mb-4 ${message.sender === 'user' ? 'flex justify-end' : 'flex justify-start'}`}>
              {message.sender === 'assistant' && (
                <div className="flex items-start max-w-[85%]">
                  <div className="bg-[#f59e0b]/20 rounded-full w-8 h-8 flex-shrink-0 flex items-center justify-center mr-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#d87706" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 3c1.5 2.2 2 4.4 2 7 0 3.8-1.6 7.7-2 11"></path>
                      <path d="M12 3c-1.5 2.2-2 4.4-2 7 0 3.8 1.6 7.7 2 11"></path>
                      <path d="M6 9a4 4 0 016-2m6 2a4 4 0 00-6-2"></path>
                      <path d="M6 15a4 4 0 104 2m4-2a4 4 0 114 2"></path>
                      <circle cx="12" cy="12" r="2"></circle>
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm text-gray-800 bg-[#f59e0b]/10 py-2 px-3 rounded-lg rounded-tl-none">{message.text}</p>
                    <p className="text-xs text-gray-600 mt-1">CTA Value Tech • {formatTime(message.timestamp)}</p>
                  </div>
                </div>
              )}
              
              {message.sender === 'user' && (
                <div className="flex flex-col items-end max-w-[85%]">
                  <div className="bg-[#10b981]/20 text-gray-800 rounded-lg py-2 px-3 text-sm">
                    {message.text}
                  </div>
                  <p className="text-xs text-gray-600 mt-1">Enviado: {formatTime(message.timestamp)}</p>
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="flex items-start max-w-[85%]">
                <div className="bg-[#f59e0b]/20 rounded-full w-8 h-8 flex-shrink-0 flex items-center justify-center mr-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#d87706" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 3c1.5 2.2 2 4.4 2 7 0 3.8-1.6 7.7-2 11"></path>
                    <path d="M12 3c-1.5 2.2-2 4.4-2 7 0 3.8 1.6 7.7 2 11"></path>
                    <path d="M6 9a4 4 0 016-2m6 2a4 4 0 00-6-2"></path>
                    <path d="M6 15a4 4 0 104 2m4-2a4 4 0 114 2"></path>
                    <circle cx="12" cy="12" r="2"></circle>
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-800 bg-[#f59e0b]/10 py-2 px-3 rounded-lg rounded-tl-none">
                    <span className="inline-block animate-pulse">...</span>
                  </p>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Input area */}
        <div className="border-t border-[#10b981]/20 p-3">
          <form onSubmit={handleSubmit} className="flex items-center">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Faça uma pergunta sobre CTA Value Tech, royalties, biodiversidade..."
              className="flex-1 border border-gray-300 rounded-lg py-2 px-3 focus:outline-none focus:ring-1 focus:ring-[#f59e0b] text-sm text-gray-800"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={input.trim() === '' || isLoading}
              className={`ml-2 ${input.trim() !== '' && !isLoading ? 'text-[#10b981]' : 'text-gray-400'}`}
              aria-label="Enviar mensagem"
            >
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                width="20" 
                height="20" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round"
              >
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatDialog;