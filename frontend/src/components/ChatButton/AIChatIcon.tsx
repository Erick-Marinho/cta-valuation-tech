// Opção 1: Robô simpático com face redonda
export const RobotIcon1 = () => (
  <svg 
    width="24" 
    height="24" 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    className="text-white"
  >
    <rect x="4" y="6" width="16" height="12" rx="2" fill="currentColor" />
    <circle cx="9" cy="10" r="1.5" fill="white" />
    <circle cx="15" cy="10" r="1.5" fill="white" />
    <path d="M9 14C10.5 16 13.5 16 15 14" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    <rect x="9" y="3" width="6" height="3" fill="currentColor" />
    <rect x="7" y="18" width="2" height="3" fill="currentColor" />
    <rect x="15" y="18" width="2" height="3" fill="currentColor" />
    <rect x="3" y="10" width="1" height="4" fill="currentColor" />
    <rect x="20" y="10" width="1" height="4" fill="currentColor" />
  </svg>
);

// Opção 2: Robô com antenas e corpo arredondado
export const RobotIcon2 = () => (
  <svg 
    width="24" 
    height="24" 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    className="text-white"
  >
    <rect x="5" y="7" width="14" height="11" rx="5" fill="currentColor" />
    <circle cx="10" cy="11" r="1.5" fill="white" />
    <circle cx="14" cy="11" r="1.5" fill="white" />
    <path d="M10 14.5C11 15.5 13 15.5 14 14.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    <path d="M9 3L8 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <path d="M15 3L16 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <rect x="8" y="18" width="2" height="3" fill="currentColor" />
    <rect x="14" y="18" width="2" height="3" fill="currentColor" />
  </svg>
);

// Opção 3: Robô com design mais moderno
export const RobotIcon3 = () => (
  <svg 
    width="24" 
    height="24" 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    className="text-white"
  >
    <path d="M12 2C8.13 2 5 5.13 5 9V15C5 15.55 5.45 16 6 16H7V9C7 6.24 9.24 4 12 4C14.76 4 17 6.24 17 9V16H18C18.55 16 19 15.55 19 15V9C19 5.13 15.87 2 12 2Z" fill="currentColor" />
    <path d="M18 16H6C4.9 16 4 16.9 4 18V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V18C20 16.9 19.1 16 18 16Z" fill="currentColor" />
    <circle cx="9" cy="19" r="1" fill="white"/>
    <circle cx="15" cy="19" r="1" fill="white"/>
    <circle cx="9" cy="10" r="1" fill="white"/>
    <circle cx="15" cy="10" r="1" fill="white"/>
    <path d="M9 14H15M9 14C9 15.6569 10.3431 17 12 17C13.6569 17 15 15.6569 15 14" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

// Opção 4: Robô amigável com cabeça ovalada
export const RobotIcon4 = () => (
  <svg 
    width="24" 
    height="24" 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    className="text-white"
  >
    <rect x="6" y="8" width="12" height="10" rx="3" fill="currentColor" />
    <rect x="8" y="2" width="8" height="6" rx="3" fill="currentColor" />
    <circle cx="10" cy="12" r="1" fill="white"/>
    <circle cx="14" cy="12" r="1" fill="white"/>
    <path d="M10 15C11 16 13 16 14 15" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    <rect x="8" y="18" width="2" height="4" fill="currentColor" />
    <rect x="14" y="18" width="2" height="4" fill="currentColor" />
  </svg>
);

// Opção 5: Robô com estilo mais ilustrado e fofo
export const RobotIcon5 = () => (
  <svg 
    width="24" 
    height="24" 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    className="text-white"
  >
    <rect x="5" y="6" width="14" height="12" rx="4" fill="currentColor" />
    <rect x="9" y="3" width="6" height="3" rx="1" fill="currentColor" />
    <circle cx="9" cy="10" r="1.5" fill="white" />
    <circle cx="15" cy="10" r="1.5" fill="white" />
    <path d="M9 13.5C10.5 15.5 13.5 15.5 15 13.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    <rect x="7" y="18" width="3" height="3" rx="1" fill="currentColor" />
    <rect x="14" y="18" width="3" height="3" rx="1" fill="currentColor" />
    <rect x="2" y="9" width="3" height="2" rx="1" fill="currentColor" />
    <rect x="19" y="9" width="3" height="2" rx="1" fill="currentColor" />
  </svg>
);

// Como usar qualquer um destes ícones no seu componente ChatButton:
/*
<button
  onClick={toggleChat}
  className={`fixed bottom-6 right-6 z-40 flex items-center justify-center gap-3 px-5 py-3 rounded-full bg-[#10b981] hover:bg-[#059669] text-white shadow-lg transition-all duration-300 ${
    animate ? 'animate-pulse' : ''
  } ${isOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
  aria-label="Conversar com o Assistente CTA"
>
  <RobotIcon1 />
  <span className="font-medium text-base whitespace-nowrap">Assistente CTA</span>
</button>
*/

