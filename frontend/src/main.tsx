import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { ChakraProvider } from '@chakra-ui/react'
import theme from './theme'
import { BrowserRouter } from 'react-router-dom'
import 'react-datepicker/dist/react-datepicker.css'

// --- Регистрация локали для react-datepicker ---
import { registerLocale, setDefaultLocale } from  "react-datepicker";
import { ru } from 'date-fns/locale'; // Убедитесь, что date-fns установлена
registerLocale('ru', ru);
setDefaultLocale('ru');
// --- Конец регистрации локали ---

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ChakraProvider theme={theme}>
        <App />
      </ChakraProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
