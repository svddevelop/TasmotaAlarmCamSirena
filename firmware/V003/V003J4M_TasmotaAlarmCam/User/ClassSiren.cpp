//#define DEBUG__

#include "ClassSieren.h"
#include "SYS/millis.h"

//#include "SYS/millis.h"
#include "sirendefines.h"




uint64_t get_systick() {
   
   /*
    uint64_t cnt = STK->CNT;
    return (cnt);  
    */
    static uint64_t last_cnt = 0;
    static uint64_t ms_acc   = 0;
    uint64_t cnt = STK->CNT;
    
    ms_acc += (uint32_t)(cnt - last_cnt);   
    last_cnt = cnt;
    uint64_t ms = ms_acc / (F_CPU / 1000);
    ms_acc -= ms * (F_CPU / 1000);
    return ms;

}

// ---------------------------------------------------------------------------
// Input debouncer: a new level is accepted only after it has been stable
// for ALARM_DEBOUNCE_MS
// ---------------------------------------------------------------------------
bool Debounce::update(bool a_raw, uint32_t a_now)
{
    if ( a_raw != last_raw )
    {
        // the input has changed -> restart the settling time
        last_raw = a_raw;
        stamp    = a_now;
    }
    else if ( (uint32_t)(a_now - stamp) >= (uint32_t)ALARM_DEBOUNCE_MS )
    {
        // the input keeps its level long enough -> accept it
        level = last_raw;
    }
    return level;
}

void ClassSiren::run()
{

    this->setReedAlarmActive( isReedActive() );
    this->setEspAlarmActive( isESPBreaked() );

    // Reset condition after the 6 minutes timeout (see Description.md):
    // the reed contact must be closed (door shut to GND) AND PIN_ESPALARM
    // must not be active. Only then the siren is allowed to trigger again.
    if ( alarmFinished && reedClosed && (espAlarmActive == false) )
        alarmFinished = false;

    this->setAlarm( isAlarmActive() );

}//void ClassSiren::run()

/*
bool ClassSiren::canResetAlarmsTimeout()
{
    return 
        (! reedAlarmActive)
        &&
        (! espAlarmActive)
        &&
        (  last_espAlarmActive)
    ;
}
*/

/*
void ClassSiren::setTickPhase(bool a_phase)
{
    last_sysTick = STK->CNT;
    if ( a_phase)
        tick_duration = ALARM_PERIOD_ON;
    else
        tick_duration = ALARM_PERIOD_OFF;
}
*/

bool ClassSiren::isAlarmActive()
{
    return 
      triggerReedAlarm ;
}

// Start the alarm. The 6 minutes timeout and the 1s/500ms phase are restarted
// only for a NEW alarm; an already running alarm keeps both of them, so no
// short drop of PIN_ALARM_PS / PIN_ALARM_PS2 can happen anymore.
void ClassSiren::startAlarm()
{
    if ( triggerReedAlarm ) return;     // the alarm is already running

    triggerReedAlarm     = true;
    alarm_start_ms       = MIL_read();
    alarm_timeout        = 0;
    alarm_active_counter = 0;
    alarmPhase           = true;        // switch the siren on immediately
}

void ClassSiren::setEspAlarmActive(bool a_val)
{
    
    if ( espAlarmActive == a_val) return;

    last_espAlarmActive = espAlarmActive;
    espAlarmActive = a_val;

    if (
        (espAlarmActive == true)
        &
        (last_espAlarmActive == false)
    )
    {
        // active: allows the siren even if watching the reed is forbidden;
        // a level which is already active never restarts the alarm
        if ( ! alarmFinished )
            startAlarm();
    }    

    if (
        (espAlarmActive == false)
        &
        (last_espAlarmActive == true)
    )
    {
        // active -> inactive: reset of the siren sound
        triggerReedAlarm = false;
    }
}

void ClassSiren::setReedAlarmActive(bool a_val)
{
    if (reedAlarmActive == a_val) return;

    last_reedAlarmActive = reedAlarmActive;
    reedAlarmActive = a_val;
    //wenn Reed war auf der kurtze Zeit aktive
    //espAlarmActive = reedAlarmActive;

    if (
        (reedAlarmActive == true )
        &
        (last_reedAlarmActive == false)
    )
    {
        // even a short opening of the door switches the siren on and it
        // stays on until the reset condition is met
        if ( ! alarmFinished )
            startAlarm();
    }

}


ClassSiren::ClassSiren():
    triggerReedAlarm(false),
    reedAlarmActive(false),
    last_reedAlarmActive(false),
    espAlarmActive(false),
    last_espAlarmActive(false),
    alarm(false),

    alarmPhase(false),
    alarmFinished(false),
    reedClosed(true),               // the door is closed in the normal state
    db_reed(false),                 // reed closed -> contact to GND
    db_allow(true),                 // watching the reed is forbidden until proven
    db_esp(false),                  // no alarm from the ESP yet
    alarm_start_ms(0),

    tick_duration(0),
    alarm_timeout(0),
    alarm_active_counter(0)
{
  PIN_output(PIN_ALARM_PS);                         // Alarm signal to the Piezo-Buzzer
  PIN_output(PIN_ALARM_PS2);                        // Alarm signal to the IP-Cam
  PIN_output(PIN_ALARM_PSL);                        // Alarm signal to the ESP

  PIN_write(PIN_ALARM_PS,  ALARM_PULSE_OFF);
  PIN_write(PIN_ALARM_PS2, ALARM_PULSE_OFF);
  PIN_write(PIN_ALARM_PSL, ALARM_PULSE_OFF);

  PIN_input_PU(PIN_ALARM_INPUT);                    // Alarm activation on rise from ALARM_OFF to ALARM_ON
  PIN_input(PIN_ALARM_BREAK_A);                  //!!! Stop alarm. It going from ?   PU -FOR DEBUG AND SIMULATION ONLY
  //PIN_input(PIN_ALARM_BREAK_B);                   // With pull-up.  Stop alarm from the external button

  //#ifdef ALARMFROMESP
  #ifdef DEBUG__
  PIN_input_PU(PIN_ESPALARM); //! !!! _PU for DEBUG ONLY
  #else 
  PIN_input(PIN_ESPALARM);
  #endif
  //#endif             

}

bool ClassSiren::isReedActive()
{
    uint32_t now = MIL_read();

    // current state of the reed-contact, filtered against the contact bounce
    bool reed_open = db_reed.update( PIN_read(PIN_ALARM_INPUT) != 0, now );
    reedClosed = ( reed_open == false );

    // send current status of the reed-contact to the ESP (switch_status[13]),
    // independent of whether watching the reed is allowed or not
    PIN_write(PIN_ALARM_PSL, reed_open);

    //check, if allow to use reed and device is active
    bool pin_allow = db_allow.update( PIN_read(PIN_ALARM_BREAK_A) != 0, now );
    bool result = (pin_allow == (bool)ALLOW_ALARM_ON);    //<-- if ESP allow to witch for  the reed, then do it

    if ( result )
    {
        result = (reed_open == (bool)ALARM_ON);  
    }

    return result;
}

bool ClassSiren::isESPBreaked()
{
    // filtered against short pulses on PIN_ESPALARM (they used to switch
    // the siren off for a few microseconds and to make it click)
    bool result = db_esp.update( PIN_read(PIN_ESPALARM) != 0, MIL_read() );
    return result;
}

void ClassSiren::setAlarmPhase(bool a_val)
{
    if (alarmPhase == a_val) return;

    alarmPhase = a_val;
    if ( a_val )
        alarm_active_counter++;
}


void ClassSiren::setAlarm(bool a_state)
{
    if ( ! a_state )
    {
        // no alarm: both outputs are held low, the phase is not touched
        PIN_write(PIN_ALARM_PS,  ALARM_PULSE_OFF);
        PIN_write(PIN_ALARM_PS2, ALARM_PULSE_OFF);
        return;
    }

    // The alarm time is measured from the alarm start. The global millis
    // counter is never reset, so the 1s/500ms phase cannot be disturbed.
    alarm_timeout = MIL_read() - alarm_start_ms;

    if ( alarm_timeout > ALARM_BREAK_BY_TIME)
        alarm_timeout = ALARM_BREAK_BY_TIME;

    if (
      ( alarm_timeout >= ALARM_BREAK_BY_TIME)
      //(alarm_active_counter >= ALARM_BREAK_BY_COUNT)
    
    )
    {
        // 6 minutes (ALARM_BREAK_BY_TIME) are over: the siren is silent,
        // the camera finishes the recording. The outputs are switched off
        // exactly once - no short pulses are generated here.
        triggerReedAlarm = false;
        alarmFinished    = true;
        alarm_timeout    = ALARM_BREAK_BY_TIME;
        setAlarmPhase(false);
        PIN_write(PIN_ALARM_PS,  ALARM_PULSE_OFF);  // the siren is silent ...
        PIN_write(PIN_ALARM_PS2, ALARM_PULSE_OFF);  // ... and the camera finishes the recording
        return;
    }

    tick_duration = alarm_timeout % (ALARM_PERIOD_ON + ALARM_PERIOD_OFF);
    //alarmPhase = tick_duration <  ALARM_PERIOD_ON;
    setAlarmPhase( tick_duration <  ALARM_PERIOD_ON );

           
    PIN_write(PIN_ALARM_PS,  alarmPhase ? ALARM_PULSE_ON : ALARM_PULSE_OFF ); // <-- a sirent
    PIN_write(PIN_ALARM_PS2, ALARM_PULSE_ON ); // <-- a ESP notification: always on while the alarm runs
}
