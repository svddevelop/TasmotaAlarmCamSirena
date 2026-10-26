#pragma once

//#include "SYS/millis.h"
#include "sirendefines.h"


class ClassSiren {

    public:
        ClassSiren();

        bool isReedActive(); // get  back the state of reed contact

        bool isESPBreaked(); // check of state the alarm activation from the ESP-Chip

        void setAlarm(bool a_state);

        void run();

        void setReedAlarmActive(bool a_val);

        void setEspAlarmActive(bool a_val);

        bool isAlarmActive();

        

    public:
        bool 
             triggerReedAlarm,
             reedAlarmActive,
             last_reedAlarmActive,
             espAlarmActive ,
             last_espAlarmActive,

             alarm               //false - the siren is deactivated, true - the siren is activated
             
             ;
             static uint64_t last_sysTick ;

    protected:
        bool alarmPhase;
        
        int64_t tick_duration ;

        uint32_t alarm_timeout ;
        int64_t alarm_active_counter ;

        void setTickPhase(bool a_phase);

        bool canResetAlarmsTimeout();

        void setAlarmPhase(bool a_val);

}; //class ClassSiren