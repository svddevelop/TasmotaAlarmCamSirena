################################################################################
# MRS Version: 2.3.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../User/SYS/millis.c 

C_DEPS += \
./User/SYS/millis.d 

OBJS += \
./User/SYS/millis.o 

DIR_OBJS += \
./User/SYS/*.o \

DIR_DEPS += \
./User/SYS/*.d \

DIR_EXPANDS += \
./User/SYS/*.234r.expand \


# Each subdirectory must supply rules for building sources it contributes
User/SYS/%.o: ../User/SYS/%.c
	@	riscv-none-embed-gcc -march=rv32ecxw -mabi=ilp32e -msmall-data-limit=0 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -I"z:/WI/TASMOTA-PROJECTS/AlarmControl/firmware/V003/V003J4M_TasmotaAlarmCam/User" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

