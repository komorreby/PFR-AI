import {
  FormControl,
  FormLabel,
  Stack,
  Button,
  FormErrorMessage,
  Heading,
  Icon
} from '@chakra-ui/react';
import { FaUserClock, FaWheelchair } from 'react-icons/fa';
import { IconType } from 'react-icons';

interface PensionTypeStepProps {
  selectedValue: string | null;
  onChange: (value: string) => void;
  errorMessage?: string;
}

const pensionTypes: { value: string; label: string; icon: IconType }[] = [
  {
    value: 'retirement_standard',
    label: 'Страховая пенсия по старости (общий случай)',
    icon: FaUserClock,
  },
  {
    value: 'disability_social',
    label: 'Социальная пенсия по инвалидности',
    icon: FaWheelchair,
  },
  // TODO: Добавить другие типы пенсий с их иконками
];

function PensionTypeStep({
  selectedValue,
  onChange,
  errorMessage,
}: PensionTypeStepProps) {
  return (
    <FormControl isInvalid={!!errorMessage}>
      <Heading size="md" mb={6}>
        Выберите тип назначаемой пенсии
      </Heading>
      <FormLabel>Тип пенсии:</FormLabel>
      <Stack direction={['column', 'row']} spacing="4" align="stretch">
        {pensionTypes.map((type) => (
          <Button
            key={type.value}
            variant={selectedValue === type.value ? 'solid' : 'outline'}
            colorScheme="blue"
            onClick={() => onChange(type.value)}
            leftIcon={<Icon as={type.icon} />}
            size="lg"
            justifyContent="flex-start"
            flex={1}
            textAlign="left"
            whiteSpace="normal"
            height="auto"
            py={3}
          >
            {type.label}
          </Button>
        ))}
      </Stack>
      {errorMessage && <FormErrorMessage>{errorMessage}</FormErrorMessage>}
    </FormControl>
  );
}

export default PensionTypeStep; 