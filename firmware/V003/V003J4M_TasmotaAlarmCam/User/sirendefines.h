#pragma once

#include "SYS/system.h"                               // system functions
#include "SYS/gpio.h"                                 // GPIO functions

//#include "SYS/millis.h"
//
//        ---------------
//    1 -| PD6       PD5 |- 8
//    2 -| GND       PC4 |- 7
//    3 -| PA2       PC2 |- 6
//    4 -| VCC       PC1 |- 5
//        ---------------
//        ----------------------------------
//    1 -| PIN_ALARM_PS2  WDIO              |- 8
//    2 -| GND            PIN_ALARM_PSL     |- 7
//  * 3 -| PIN_ALARM_PS   PIN_ALARM_BREAK_A |- 6
//    4 -| VCC            PIN_ALARM_INPUT   |- 5 *
//        ----------------------------------
//

//#define PIN_LED   PC0        
#define PIN_WDIO            PD5
#define PIN_ESPALARM        PIN_WDIO  //[I] programmable alarm from ESP. For include these code-snipped need to define #ALARMFROMESP 
//#define ALARMFROMESP

#define PIN_ALARM_PS        PA2      // (O)Alarm signal to the Piezo-Buzzer
#define PIN_ALARM_PS2       PD6     // (O)Alarm signal to the Cam DI
#define PIN_ALARM_INPUT     PC1     // (I) Alarm input (reed)                     
#define PIN_ALARM_BREAK_A   PC2     // (I) the reaction                          
#define PIN_ALARM_PSL       PC4     // (O) Alarm for ESP

#define BREAK_ACTIVE        (1)
#define BREAK_INACTIVE      (0)

#define ALARM_PULSE_ON      (1)     // the Piezo-buzzer activated
#define ALARM_PULSE_OFF     (0)     // the Piezo-buzzer deactivated

#define ALLOW_ALARM_OFF     (1)     // Allow from ESP (R_I)
#define ALLOW_ALARM_ON      (0)     // <--

#define ALARM_ON            (1)
#define ALARM_OFF           (0)

// Input settling time: a level on PIN_ALARM_INPUT / PIN_ALARM_BREAK_A /
// PIN_ESPALARM must be stable this long before it is accepted.
// Rejects contact bounce, EMI and short pulses which used to cause
// the short drops on PIN_ALARM_PS / PIN_ALARM_PS2 (clicks of the siren).
#define ALARM_DEBOUNCE_MS   (30)


#define ALARM_PERIOD_ON     (1000)  // Period in ms, when the Piezo-buzzer is active

#define ALARM_PERIOD_OFF    (300)   // Period in ms, when the Piezo-buzzer is inactive


/////


#define ALARM_MUST_ACTIVE_IN_MIN  (5)


#define _ALARM_CYCLES_LONG(min)   ((uint64_t)(min) * 60ULL * 1000ULL)
#define ALARM_BREAK_BY_TIME       ((uint64_t)_ALARM_CYCLES_LONG(ALARM_MUST_ACTIVE_IN_MIN))


#define ALARM_BREAK_BY_COUNT        (240)

#define ALARM_PS(x)         PIN_write(PIN_ALARM_PS, x);PIN_write(PIN_ALARM_PS2, x)
