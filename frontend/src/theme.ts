
import { extendTheme, ThemeConfig } from '@chakra-ui/react';
import { mode, transparentize, StyleFunctionProps } from '@chakra-ui/theme-tools';

// 1. Цвета
// Определяем основные цвета бренда с необходимыми оттенками
const colors = {
  brand: {
    white: '#FFFFFF',
    blue: {
      50: '#E6F0FF',  // Очень светлый синий (для hover на outline кнопках)
      100: '#CCE1FF',
      200: '#99C3FF',
      300: '#66A5FF',
      400: '#3387FF',
      500: '#0039A6', // Основной синий (Российский флаг)
      600: '#002D84', // Темнее для hover/active
      700: '#002163', // Еще темнее
      800: '#001541',
      900: '#000A20',
    },
    red: {
      50: '#FDEDEC',   // Очень светлый красный (для hover на outline кнопках)
      100: '#FAD9D7',
      200: '#F6B3AF',
      300: '#F18D87',
      400: '#ED675F',
      500: '#D52B1E',  // Основной красный (Российский флаг)
      600: '#B82013', // Темнее для hover/active
      700: '#9A170A', // Еще темнее
      800: '#7D0E00',
      900: '#600500',
    },
  },
  // Используем стандартные серые цвета Chakra, они хорошо подобраны
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
  // Стандартные цвета Chakra для семантики, если они нужны напрямую
  // или если компоненты ожидают полную палитру для colorScheme
  teal: {
    50: '#E6FFFA', 100: '#B2F5EA', 200: '#81E6D9', 300: '#4FD1C5', 400: '#38B2AC',
    500: '#319795', 600: '#2C7A7B', 700: '#285E61', 800: '#234E52', 900: '#1D4044',
  },
  orange: {
    50: '#FFF5E6', 100: '#FFEBC6', 200: '#FEE0A3', 300: '#FDD580', 400: '#FCCB5D',
    500: '#FBC02D', 600: '#E9AD00', 700: '#D09900', 800: '#B78600', 900: '#9E7200',
  },
  green: {
    50: '#F0FFF4', 100: '#C6F6D5', 200: '#9AE6B4', 300: '#68D391', 400: '#48BB78',
    500: '#38A169', 600: '#2F855A', 700: '#276749', 800: '#22543D', 900: '#1C4532',
  },
};

// 2. Семантические токены
const semanticTokens = {
  colors: {
    // Брендовые цвета
    primary: 'brand.blue.500',
    primaryHover: 'brand.blue.600',
    primaryActive: 'brand.blue.700',
    danger: 'brand.red.500',
    dangerHover: 'brand.red.600',
    dangerActive: 'brand.red.700',

    // Семантические состояния
    success: 'green.500',
    successHover: 'green.600',
    warning: 'orange.500',
    warningHover: 'orange.600',
    info: 'teal.500',
    infoHover: 'teal.600',

    // Текст
    text: { default: 'gray.800', _dark: 'gray.100' },
    textSecondary: { default: 'gray.600', _dark: 'gray.400' },
    textInverse: { default: 'gray.100', _dark: 'gray.800' }, // для текста на темных/светлых фонах
    textDisabled: { default: 'gray.400', _dark: 'gray.500' },

    // Фон
    background: { default: 'gray.50', _dark: 'gray.800' },
    backgroundAlt: { default: 'brand.white', _dark: 'gray.700' }, // Альтернативный фон, например, для карточек
    
    // Границы
    border: { default: 'gray.200', _dark: 'gray.600' },
    borderStrong: { default: 'gray.300', _dark: 'gray.500'},

    // Элементы UI
    focusRing: { default: 'brand.blue.500', _dark: 'brand.blue.300' }, // Цвет для кольца фокуса
    cardBackground: { default: 'brand.white', _dark: 'gray.700' }, // Уже было, но подтверждаем

    // Специальные для компонентов (если нужно)
    buttonDisabledBg: { default: 'gray.200', _dark: 'gray.600' },
    buttonDisabledText: { default: 'gray.500', _dark: 'gray.400'}
  },
};

// 3. Конфигурация темы
const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: false,
};

// 4. Стили компонентов
const components = {
  Button: {
    baseStyle: {
      fontWeight: 'bold',
      borderRadius: 'md', // Слегка скруглим углы по умолчанию
      _focusVisible: (props: StyleFunctionProps) => ({ // Улучшенный стиль фокуса
        boxShadow: `0 0 0 3px ${transparentize(semanticTokens.colors.focusRing.default, 0.6)(props.theme)}`,
        _dark: {
            boxShadow: `0 0 0 3px ${transparentize(semanticTokens.colors.focusRing._dark, 0.6)(props.theme)}`,
        }
      }),
    },
    variants: {
      solid: (props: StyleFunctionProps) => {
        const { colorScheme: c } = props;
        let bg = `${c}.500`;
        let color = 'brand.white'; // По умолчанию для ярких схем
        let hoverBg = `${c}.600`;
        let activeBg = `${c}.700`;

        if (c === 'primary') {
          bg = 'primary';
          hoverBg = 'primaryHover';
          activeBg = 'primaryActive';
        } else if (c === 'danger') {
          bg = 'danger';
          hoverBg = 'dangerHover';
          activeBg = 'dangerActive';
        } else if (c === 'gray') { // Для серых кнопок текст обычно темный
            color = 'text'; // или gray.800
            // hover и active для gray уже хорошо обрабатываются Chakra
        }
        // Для других colorScheme (green, teal, orange) используется стандартная логика c.500, c.600, c.700

        return {
          bg,
          color,
          _hover: {
            bg: hoverBg,
            _disabled: { // Важно для предотвращения изменения стиля hover на disabled кнопках
              bg, // или 'buttonDisabledBg'
            },
          },
          _active: {
            bg: activeBg,
          },
          _disabled: {
            bg: 'buttonDisabledBg',
            color: 'buttonDisabledText',
            opacity: 0.7, // Chakra по умолчанию использует opacity для disabled
            cursor: 'not-allowed',
          }
        };
      },
      outline: (props: StyleFunctionProps) => {
        const { colorScheme: c } = props;
        let color = 'text';
        let borderColor = 'border';
        let hoverBgKeyLight = 'gray.100';
        let hoverBgKeyDark = 'gray.700'; // или whiteAlpha.100

        if (c === 'primary') {
          color = 'primary';
          borderColor = 'primary';
          hoverBgKeyLight = 'brand.blue.50';
          hoverBgKeyDark = transparentize('primary', 0.12)(props.theme); // alpha 12% от primary
        } else if (c === 'danger') {
          color = 'danger';
          borderColor = 'danger';
          hoverBgKeyLight = 'brand.red.50';
          hoverBgKeyDark = transparentize('danger', 0.12)(props.theme); // alpha 12% от danger
        } else if (c !== 'gray') { // Для стандартных цветных схем
            color = `${c}.500`; // e.g. green.500
            borderColor = `${c}.500`;
             _dark: { // В темном режиме цвет текста для outline может быть светлее
                color: `${c}.300`;
                borderColor: `${c}.300`;
            }
            hoverBgKeyLight = `${c}.50`;
            hoverBgKeyDark = transparentize(`${c}.500`, 0.12)(props.theme);
        }
        // Для colorScheme="gray", color и borderColor остаются 'text' и 'border'


        return {
          color,
          borderColor,
          _hover: {
            bg: mode(hoverBgKeyLight, hoverBgKeyDark)(props),
          },
           _disabled: {
            color: 'buttonDisabledText',
            borderColor: 'buttonDisabledBg', // или 'transparent' если не нужна рамка
            bg: 'transparent', // Обычно outline кнопки не имеют фона в disabled
            opacity: 0.5,
            cursor: 'not-allowed',
          }
        };
      },
    },
    defaultProps: {
      colorScheme: 'primary', // По умолчанию кнопки будут использовать 'primary' colorScheme
    },
  },
  Card: { // Стили для карточек
    baseStyle: (props: StyleFunctionProps) => ({ // Превращаем в функцию для доступа к props, если нужно
        container: {
            bg: mode('cardBackground.default', 'cardBackground._dark')(props), // Используем mode для явности
            borderWidth: '1px',
            borderColor: mode('border.default', 'border._dark')(props),
            borderRadius: 'md',
            boxShadow: mode('sm', 'md')(props), // Тень может быть разной в темах
            transition: 'background-color 0.2s ease-out, border-color 0.2s ease-out, box-shadow 0.2s ease-out',
        }
    }),
    // Можно добавить variants или sizes, если нужно
  },
  Tag: {
    baseStyle: {
         borderRadius: 'full', // Оставляем круглыми по умолчанию
         fontWeight: 'medium', // Чуть менее жирный, чем у кнопок
    },
    variants: {
         solid: (props: StyleFunctionProps) => {
            const { colorScheme: c } = props;
            let bg = `${c}.500`;
            let color = 'brand.white'; // По умолчанию для ярких схем

            if (c === 'primary') {
                bg = 'primary';
            } else if (c === 'danger') {
                bg = 'danger';
            } else if (c === 'gray') {
                bg = 'gray.200'; // Светло-серый фон для серых тегов
                color = 'gray.800'; // Темный текст
                _dark: { // Для темной темы
                    bg: 'gray.600';
                    color: 'gray.100';
                }
            }
            // Для других colorScheme (green, teal, orange) используется стандартная логика `${c}.500`
            
            return {
                bg,
                color,
            };
         }
        // Можно добавить другие варианты, например, 'outline' или 'subtle'
    },
    defaultProps: {
        colorScheme: 'gray', // Серый тег по умолчанию, чтобы не был слишком ярким
    }
  },
  Alert: {
    baseStyle: {
        container: {
             borderRadius: 'md', // Оставляем скругление
        }
    },
    // Можно добавить кастомные варианты или переопределить существующие (e.g. 'subtle', 'left-accent')
  },
  // Стили для других компонентов можно добавлять здесь
  // Например, Input, Select, Modal и т.д.
};

// 5. Глобальные стили
const styles = {
  global: (props: StyleFunctionProps) => ({
    'html, body': {
      color: mode('text.default', 'text._dark')(props), // Явное использование mode
      bg: mode('background.default', 'background._dark')(props),
      lineHeight: 'tall', // 1.625 (из стандартных размеров Chakra)
      fontSize: 'md', // Убедимся, что базовый размер шрифта установлен
      WebkitFontSmoothing: 'antialiased', // Улучшение рендеринга шрифтов
      MozOsxFontSmoothing: 'grayscale',
      transitionProperty: 'background-color, color', // Плавные переходы для темы
      transitionDuration: '0.2s',
      transitionTimingFunction: 'ease-out',
    },
    a: {
      color: mode('primary', 'brand.blue.300')(props), // Ссылки чуть светлее в темной теме для контраста
      fontWeight: 'medium',
      textDecoration: 'none', // Убираем подчеркивание по умолчанию
      _hover: {
        textDecoration: 'underline',
        color: mode('primaryHover', 'brand.blue.200')(props),
      },
    },
    // Можно добавить стили для заголовков (h1-h6), параграфов (p) и т.д.
    'h1, h2, h3, h4, h5, h6': {
        fontWeight: 'bold',
        color: mode('gray.900', 'brand.white')(props), // Заголовки темнее/белые
    },
    h1: { fontSize: '3xl', mb: 4 }, // Примерные размеры и отступы
    h2: { fontSize: '2xl', mb: 3 },
    h3: { fontSize: 'xl', mb: 2 },

    '*::placeholder': { // Стили для плейсхолдеров
        color: mode('gray.400', 'gray.500')(props),
        opacity: 1,
    },
    '*, *::before, *::after': {
        borderColor: mode('border.default', 'border._dark')(props), // По умолчанию цвет границ
        wordWrap: 'break-word',
    },
    // Стили для фокуса, если стандартный outline не используется
    // ':focus-visible:not([data-focus-visible-disabled])': {
    //   boxShadow: `0 0 0 3px ${transparentize(semanticTokens.colors.focusRing.default, 0.6)(props.theme)}`,
    //   _dark: {
    //       boxShadow: `0 0 0 3px ${transparentize(semanticTokens.colors.focusRing._dark, 0.6)(props.theme)}`,
    //   },
    //   outline: 'none',
    // },
  }),
};

// 6. Собираем и экспортируем тему
const theme = extendTheme({
  config,
  colors,
  semanticTokens,
  components,
  styles,
  // Можно также переопределить шрифты, размеры, отступы и т.д.
  // fonts: {
  //   heading: `'Your Heading Font', sans-serif`,
  //   body: `'Your Body Font', sans-serif`,
  // },
  // space: { ... },
  // fontSizes: { ... },
  // radii: { ... },
});

export default theme;
