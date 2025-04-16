import { extendTheme, ThemeConfig } from '@chakra-ui/react'

// Цвета Российского флага
const colors = {
  brand: {
    white: '#FFFFFF',
    blue: '#0039A6', // Синий
    red: '#D52B1E',  // Красный
  },
  // Дополнительные нейтральные цвета для текста, фона и т.д.
  gray: {
    50: '#f7fafc',
    100: '#edf2f7',
    200: '#e2e8f0',
    300: '#cbd5e0',
    400: '#a0aec0',
    500: '#718096',
    600: '#4a5568',
    700: '#2d3748',
    800: '#1a202c',
    900: '#171923',
  },
}

// 2. Определяем семантические токены (если нужно переопределить стандартные цвета Chakra)
const semanticTokens = {
  colors: {
    primary: 'brand.blue',
    danger: 'brand.red',
    text: 'gray.800',
    background: 'gray.50',
    cardBackground: 'brand.white',
    border: 'gray.200',
  },
}

// 3. Конфигурация темы (например, начальный цветовой режим)
const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: false,
}

// 4. Создаем тему
const theme = extendTheme({
  config,
  colors,
  semanticTokens,
  components: {
    Button: {
      baseStyle: {
        fontWeight: 'bold',
      },
      variants: {
        solid: (props: { colorScheme: string }) => ({
          bg: props.colorScheme === 'primary' ? 'primary' : undefined,
          color: props.colorScheme === 'primary' ? 'brand.white' : undefined,
          _hover: {
             bg: props.colorScheme === 'primary' ? 'brand.blue' : undefined, // Можно добавить легкое затемнение/осветление
             opacity: 0.9
          }
        }),
         outline: (props: { colorScheme: string }) => ({
          borderColor: props.colorScheme === 'primary' ? 'primary' : 'border',
          color: props.colorScheme === 'primary' ? 'primary' : 'text',
        }),
      },
      defaultProps: {
        colorScheme: 'primary', // По умолчанию кнопки будут синими
      },
    },
    Card: { // Стили для карточек (используем в HistoryList)
        baseStyle: {
            container: {
                bg: 'cardBackground',
                borderWidth: '1px',
                borderColor: 'border',
                borderRadius: 'md',
                boxShadow: 'sm'
            }
        }
    },
     Alert: { // Стили для уведомлений об ошибках
        baseStyle: {
            container: {
                 borderRadius: 'md',
            }
        }
    }
    // Можно добавить стили для других компонентов по мере необходимости
  },
  styles: {
    global: {
      'html, body': {
        color: 'text',
        bg: 'background',
        lineHeight: 'tall',
      },
      a: {
        color: 'primary',
        _hover: {
          textDecoration: 'underline',
        },
      },
    },
  }
})

export default theme 