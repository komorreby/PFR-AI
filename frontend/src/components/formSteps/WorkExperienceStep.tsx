import React from 'react';
import { Control, Controller, FieldErrors, UseFormRegister, UseFormGetValues, UseFieldArrayAppend, UseFieldArrayRemove, FieldArrayWithId } from 'react-hook-form';
import DatePicker from "react-datepicker";
import { parse } from 'date-fns';
import {
    VStack,
    Heading,
    SimpleGrid,
    FormControl,
    FormLabel,
    Input,
    FormErrorMessage,
    NumberInput,
    NumberInputField,
    NumberInputStepper,
    NumberIncrementStepper,
    NumberDecrementStepper,
    Divider,
    Checkbox,
    Box,
    HStack,
    IconButton,
    Button
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { CaseFormDataTypeForRHF, WorkRecord } from '../../types';
import CustomDateInput from '../formInputs/CustomDateInput';
import { formatDateForInput } from '../../utils';

interface WorkExperienceStepProps {
    control: Control<CaseFormDataTypeForRHF>;
    register: UseFormRegister<CaseFormDataTypeForRHF>;
    errors: FieldErrors<CaseFormDataTypeForRHF>;
    fields: FieldArrayWithId<CaseFormDataTypeForRHF, "work_experience.records", "id">[];
    append: UseFieldArrayAppend<CaseFormDataTypeForRHF, "work_experience.records">;
    remove: UseFieldArrayRemove;
    getErrorMessage: (name: string) => string | undefined;
    getValues: UseFormGetValues<CaseFormDataTypeForRHF>;
}

const WorkExperienceStep: React.FC<WorkExperienceStepProps> = ({ 
    control, register, fields, append, remove, getErrorMessage, getValues
}) => {
    return (
        <VStack spacing={4} align="stretch">
            <Heading size="md" mb={4}>Трудовой стаж</Heading>
            <FormControl isInvalid={!!getErrorMessage('work_experience.total_years')}>
              <FormLabel htmlFor="total_years">Общий подтвержденный стаж (лет)</FormLabel>
              <Controller
                name="work_experience.total_years"
                control={control}
                rules={{ 
                    required: "Общий стаж обязателен", 
                    min: { value: 0, message: "Стаж не может быть отрицательным" },
                    validate: value => typeof value === 'number' || "Значение должно быть числом"
                }}
                render={({ field }) => (
                    <NumberInput 
                        id="total_years" 
                        min={0} 
                        precision={1} 
                        step={0.5}
                        value={field.value === undefined || field.value === null ? '' : String(field.value)}
                        onChange={(_valueAsString, valueAsNumber) => field.onChange(valueAsNumber)}
                        onBlur={field.onBlur}
                    >
                        <NumberInputField ref={field.ref} />
                        <NumberInputStepper><NumberIncrementStepper /><NumberDecrementStepper /></NumberInputStepper>
                    </NumberInput>
                )}
              />
               <FormErrorMessage>{getErrorMessage('work_experience.total_years')}</FormErrorMessage>
            </FormControl>

             <Divider my={4} />
             <Heading size="sm" mb={2}>Записи о трудовой деятельности</Heading>

             <VStack spacing={4} align="stretch">
                {fields.map((item, index) => (
                  <Box key={item.id} p={4} borderWidth="1px" borderRadius="md" borderColor="gray.200">
                     <Heading size="xs" mb={3}>Место работы #{index + 1}</Heading>
                      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                          <FormControl isInvalid={!!getErrorMessage(`work_experience.records.${index}.organization`)}>
                              <FormLabel htmlFor={`work_experience.records.${index}.organization`}>Организация</FormLabel>
                              <Input 
                                id={`work_experience.records.${index}.organization`} 
                                {...register(`work_experience.records.${index}.organization` as const, { required: "Организация обязательна" })} 
                              />
                               <FormErrorMessage>{getErrorMessage(`work_experience.records.${index}.organization`)}</FormErrorMessage>
                           </FormControl>
                           <FormControl isInvalid={!!getErrorMessage(`work_experience.records.${index}.position`)}>
                              <FormLabel htmlFor={`work_experience.records.${index}.position`}>Должность</FormLabel>
                              <Input 
                                id={`work_experience.records.${index}.position`} 
                                {...register(`work_experience.records.${index}.position` as const, { required: "Должность обязательна" })} 
                              />
                               <FormErrorMessage>{getErrorMessage(`work_experience.records.${index}.position`)}</FormErrorMessage>
                           </FormControl>
                            <FormControl isInvalid={!!getErrorMessage(`work_experience.records.${index}.start_date`)}>
                               <FormLabel htmlFor={`work_experience.records.${index}.start_date`}>Дата начала</FormLabel>
                               <Controller
                                   name={`work_experience.records.${index}.start_date` as const}
                                   control={control}
                                   rules={{ required: "Дата начала обязательна" }}
                                   render={({ field }) => (
                                       <DatePicker
                                          selected={field.value ? parse(field.value, 'yyyy-MM-dd', new Date()) : null}
                                          onChange={(date: Date | null) => field.onChange(formatDateForInput(date))}
                                          locale="ru"
                                          showYearDropdown scrollableYearDropdown yearDropdownItemNumber={100}
                                          maxDate={new Date()}
                                          customInput={ <CustomDateInput id={field.name} fieldOnChange={field.onChange} maxDate={new Date()} /> }
                                          dateFormat="dd.MM.yyyy" placeholderText="ДД.ММ.ГГГГ" autoComplete="off" shouldCloseOnSelect={true}
                                        />
                                   )}
                               />
                                <FormErrorMessage>{getErrorMessage(`work_experience.records.${index}.start_date`)}</FormErrorMessage>
                            </FormControl>
                            <FormControl isInvalid={!!getErrorMessage(`work_experience.records.${index}.end_date`)}>
                               <FormLabel htmlFor={`work_experience.records.${index}.end_date`}>Дата окончания</FormLabel>
                                <Controller
                                   name={`work_experience.records.${index}.end_date` as const}
                                   control={control}
                                   rules={{ 
                                       required: "Дата окончания обязательна",
                                       validate: value => {
                                           const startDate = getValues(`work_experience.records.${index}.start_date`);
                                           if (startDate && value && parse(value, 'yyyy-MM-dd', new Date()) < parse(startDate, 'yyyy-MM-dd', new Date())) {
                                               return "Дата окончания не может быть раньше даты начала";
                                           }
                                           return true;
                                       }
                                    }}
                                   render={({ field }) => (
                                       <DatePicker
                                          selected={field.value ? parse(field.value, 'yyyy-MM-dd', new Date()) : null}
                                          onChange={(date: Date | null) => field.onChange(formatDateForInput(date))}
                                          locale="ru"
                                          showYearDropdown scrollableYearDropdown yearDropdownItemNumber={100}
                                          minDate={getValues(`work_experience.records.${index}.start_date`) ? parse(getValues(`work_experience.records.${index}.start_date`), 'yyyy-MM-dd', new Date()) : undefined}
                                          maxDate={new Date()}
                                          customInput={ <CustomDateInput id={field.name} fieldOnChange={field.onChange} maxDate={new Date()} /> }
                                          dateFormat="dd.MM.yyyy" placeholderText="ДД.ММ.ГГГГ" autoComplete="off" shouldCloseOnSelect={true}
                                       />
                                   )}
                               />
                               <FormErrorMessage>{getErrorMessage(`work_experience.records.${index}.end_date`)}</FormErrorMessage>
                            </FormControl>
                       </SimpleGrid>
                       <HStack mt={4} justify="space-between">
                          <FormControl display="flex" alignItems="center" width="auto">
                              <Checkbox 
                                id={`work_experience.records.${index}.special_conditions`} 
                                {...register(`work_experience.records.${index}.special_conditions` as const)} 
                                mr={2} 
                              />
                              <FormLabel htmlFor={`work_experience.records.${index}.special_conditions`} mb="0">Особые условия труда</FormLabel>
                           </FormControl>
                           <IconButton aria-label="Удалить место работы" icon={<DeleteIcon />} colorScheme="red" variant="ghost" size="sm" onClick={() => remove(index)} />
                        </HStack>
                   </Box>
                ))}
             </VStack>

             <Button
                leftIcon={<AddIcon />}
                onClick={() => append({ organization: '', start_date: '', end_date: '', position: '', special_conditions: false } as WorkRecord) }
                variant="outline" colorScheme="green" size="sm" mt={4}
             >
               Добавить место работы
             </Button>
        </VStack>
    );
};

export default WorkExperienceStep; 