'use client';

import { Bot } from 'lucide-react';
import { useEffect, useState } from 'react';
import ChatDialog from '../ChatDialog';
const ChatButton = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [animate, setAnimate] = useState(false);
  const [slideDirection, setSlideDirection] = useState('');
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Animação de pulso para o botão quando carregado pela primeira vez
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimate(true);
    }, 2000);

    const resetAnimation = setTimeout(() => {
      setAnimate(false);
    }, 5000);

    return () => {
      clearTimeout(timer);
      clearTimeout(resetAnimation);
    };
  }, []);

  const toggleChat = () => {
    setIsTransitioning(true);
    
    if (!isOpen) {
      // Ao abrir o chat, slide da direita para a esquerda (saindo)
      setSlideDirection('slide-left');
      setTimeout(() => {
        setIsOpen(true);
        setIsTransitioning(false);
      }, 300);
    } else {
      // Ao fechar o chat
      setIsOpen(false);
      // Aguarda um pouco para o diálogo desaparecer antes de mostrar o botão
      setTimeout(() => {
        // Ao mostrar novamente, slide da esquerda para a direita (entrando)
        setSlideDirection('slide-right');
        setTimeout(() => {
          setSlideDirection('');
          setIsTransitioning(false);
        }, 300);
      }, 100);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    // Aguarda um pouco para o diálogo desaparecer antes de mostrar o botão
    setTimeout(() => {
      // Ao mostrar novamente, slide da esquerda para a direita (entrando)
      setSlideDirection('slide-right');
      setTimeout(() => {
        setSlideDirection('');
      }, 300);
    }, 100);
  };

  // Determina classes de animação com base no estado
  const getButtonClasses = () => {
    const baseClasses = "fixed bottom-6 right-6 z-40 flex items-center justify-center gap-3 px-8 py-4 rounded-full bg-[#10b981] hover:bg-[#059669] text-white shadow-lg transition-all duration-300 ease-in-out cursor-pointer";
    
    if (isOpen || (isTransitioning && slideDirection === 'slide-left')) {
      return `${baseClasses} opacity-0 transform translate-x-10 pointer-events-none`;
    }
    
    if (slideDirection === 'slide-right') {
      return `${baseClasses} opacity-100 transform translate-x-0 animate-slide-in-right`;
    }
    
    return `${baseClasses} opacity-100 ${animate ? 'animate-pulse' : ''}`;
  };

  return (
    <>
      <style jsx global>{`
        @keyframes slideInRight {
          from {
            transform: translateX(-50px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        
        .animate-slide-in-right {
          animation: slideInRight 0.3s ease-out forwards;
        }
      `}</style>
      
      <button
        onClick={toggleChat}
        className={getButtonClasses()}
        aria-label="Conversar com o Assistente CTA"
      >
        {/* <RobotIcon2 /> */}
        <Bot size={28} strokeWidth={2.5} className="text-center" />
        <span className="font-medium text-base whitespace-nowrap text-[16px] pt-1">Assistente CTA</span>
      </button>
      
      <ChatDialog isOpen={isOpen} onClose={handleClose} />
    </>
  );
};

export default ChatButton;