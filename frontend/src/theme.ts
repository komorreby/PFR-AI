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
  // Добавляем стандартные цвета Chakra для семантики, если свои не нужны
  teal: { // Для info
    50: '#E6FFFA',
    100: '#B2F5EA',
    200: '#81E6D9',
    300: '#4FD1C5',
    400: '#38B2AC',
    500: '#319795',
    600: '#2C7A7B',
    700: '#285E61',
    800: '#234E52',
    900: '#1D4044',
  },
  orange: { // Для warning
    50: '#FFF5E6',
    100: '#FFEBC6',
    200: '#FEE0A3',
    300: '#FDD580',
    400: '#FCCB5D',
    500: '#FBC02D', // Chakra orange.500
    600: '#E9AD00',
    700: '#D09900',
    800: '#B78600',
    900: '#9E7200',
  },
  green: { // Для success
    50: '#F0FFF4',
    100: '#C6F6D5',
    200: '#9AE6B4',
    300: '#68D391',
    400: '#48BB78',
    500: '#38A169', // Chakra green.500
    600: '#2F855A',
    700: '#276749',
    800: '#22543D',
    900: '#1C4532',
  },
}

// 2. Определяем семантические токены (если нужно переопределить стандартные цвета Chakra)
const semanticTokens = {
  colors: {
    primary: 'brand.blue',
    danger: 'brand.red',
    success: 'green.500',
    warning: 'orange.500',
    info: 'teal.500',
    text: { default: 'gray.800', _dark: 'gray.100' },
    textSecondary: { default: 'gray.600', _dark: 'gray.400' },
    background: { default: 'gray.50', _dark: 'gray.800' },
    cardBackground: { default: 'brand.white', _dark: 'gray.700' },
    border: { default: 'gray.200', _dark: 'gray.600' },
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
          borderColor: props.colorScheme === 'primary' ? 'primary' :
                       props.colorScheme === 'danger' ? 'danger' : 'border',
          color: props.colorScheme === 'primary' ? 'primary' :
                 props.colorScheme === 'danger' ? 'danger' : 'text',
          _hover: {
             bg: props.colorScheme === 'primary' ? 'blue.50' :
                 props.colorScheme === 'danger' ? 'red.50' : 'gray.100',
            _dark: {
                bg: props.colorScheme === 'primary' ? 'rgba(0, 57, 166, 0.1)' :
                    props.colorScheme === 'danger' ? 'rgba(213, 43, 30, 0.1)' : 'gray.700',
            }
          }
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
                boxShadow: 'sm',
                transition: 'background-color 0.2s ease-out, border-color 0.2s ease-out'
            }
        }
    },
    Tag: {
        baseStyle: {
             borderRadius: 'full',
        },
        variants: {
             solid: (props: { colorScheme: string }) => ({
                 bg: `${props.colorScheme}.500`,
                 color: 'white',
             })
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
        transition: 'background-color 0.2s ease-out, color 0.2s ease-out'
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