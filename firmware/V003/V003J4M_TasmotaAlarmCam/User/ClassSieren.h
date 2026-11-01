#pragma once

//#include "SYS/millis.h"
#include "sirendefines.h"


// ---------------------------------------------------------------------------
// Debounced input.
//
// A new level is accepted only after it has been stable for ALARM_DEBOUNCE_MS.
// Contact bounce, EMI and short pulses on PIN_ESPALARM / PIN_ALARM_INPUT /
// PIN_ALARM_BREAK_A used to switch the alarm trigger on and off for a few
// microseconds, which produced the short drops on PIN_ALARM_PS and
// PIN_ALARM_PS2 (the audible "clicks" of the siren).
// ---------------------------------------------------------------------------
struct Debounce {
    bool     level;      // filtered (stable) level
    bool     last_raw;   // last raw sample
    uint32_t stamp;      // time of the last raw change

    Debounce(bool a_init = false): level(a_init), last_raw(a_init), stamp(0) {}

    bool update(bool a_raw, uint32_t a_now);
};


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
        bool alarmFinished;         // the 6 minutes are over -> the siren is locked
                                    // until the reset condition is met
        bool reedClosed;            // reed contact is closed (door shut -> to GND)

        Debounce db_reed;           // PIN_ALARM_INPUT   (reed contact)
        Debounce db_allow;          // PIN_ALARM_BREAK_A (watching allowed by ESP)
        Debounce db_esp;            // PIN_ESPALARM      (reset / sound from ESP)

        uint32_t alarm_start_ms;    // monotonic MIL time of the alarm start

        int64_t tick_duration ;

        uint32_t alarm_timeout ;
        int64_t alarm_active_counter ;

        void startAlarm();

        void setTickPhase(bool a_phase);

        bool canResetAlarmsTimeout();

        void setAlarmPhase(bool a_phase);

}; //class ClassSiren
