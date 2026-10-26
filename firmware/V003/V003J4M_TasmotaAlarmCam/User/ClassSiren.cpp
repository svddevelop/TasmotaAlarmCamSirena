//#define DEBUG__

#include "ClassSieren.h"
#include "millis.h"

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
    // STK ¡ª 32-§Ò§Ú§ä§ß§í§Û §Ú §á§Ö§â§Ö§á§à§Ý§ß§ñ§Ö§ä§ã§ñ §Ü§Ñ§Ø§Õ§í§Ö ~89 c §á§â§Ú 48 §®§¤§è!
    ms_acc += (uint32_t)(cnt - last_cnt);   // §å§é§Ú§ä§í§Ó§Ñ§Ö§Þ wrap-around
    last_cnt = cnt;
    uint64_t ms = ms_acc / (F_CPU / 1000);
    ms_acc -= ms * (F_CPU / 1000);
    return ms;

}

void ClassSiren::run()
{

    this->setReedAlarmActive( isReedActive() );
    this->setEspAlarmActive( isESPBreaked() );

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
        triggerReedAlarm = true;
        alarm_timeout = 0;
        alarm_active_counter = 0;
        MIL_reset();
    }    

    if (
        (espAlarmActive == false)
        &
        (last_espAlarmActive == true)
    )
    {
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
        triggerReedAlarm = true;
        alarm_timeout = 0;
        alarm_active_counter = 0;
        MIL_reset();
    }

}


ClassSiren::ClassSiren():
    reedAlarmActive(false),
    last_reedAlarmActive(false),
    last_espAlarmActive(false),
    espAlarmActive(false),
    alarm(false),
    alarmPhase(false),
    
    tick_duration(0),
    alarm_timeout(0),
    triggerReedAlarm(false),
    alarm_active_counter(0)
{
  PIN_output(PIN_ALARM_PS);                         // Alarm signal to the Piezo-Buzzer
  PIN_output(PIN_ALARM_PS2);                        // Alarm signal to the Piezo-Buzzer
  PIN_output(PIN_ALARM_PSL);                        // Alarm signal to the ESP
  PIN_write(PIN_ALARM_PS, ALARM_PERIOD_OFF);
  PIN_write(PIN_ALARM_PS2, ALARM_PERIOD_OFF);
  PIN_write(PIN_ALARM_PSL, ALARM_PERIOD_OFF);

  PIN_input_PU(PIN_ALARM_INPUT);                    // Alarm activation on reise from ALARM_OFF to ALARM_ON
  PIN_input(PIN_ALARM_BREAK_A);                  //!!! Stop alarm. It going from ?   PU -FOR DEBUG AND SIMULATION ONLY
  //PIN_input(PIN_ALARM_BREAK_B);                   // With pull-up.  Stop alarm from the external button

  //#ifdef ALARMFROMESP
  #ifdef DEBUG__
  PIN_input_PU(PIN_ESPALARM); //! !!! _PU for DEBUG ONLY
  #else 
  PIN_input(PIN_ESPALARM);
  #endif
  //#endif    

  PIN_write(PIN_ALARM_PS, ALARM_PULSE_OFF);
  PIN_write(/*PIN_ALARM_PS2*/PA3, ALARM_PULSE_OFF);  


  // 
  /*  STK->CMP  = (F_CPU / 1000) - 1;   // 1 §Þ§ã
    STK->CTLR |= STK_CTLR_STIE;       // §Ó§Ü§Ý§ð§é§Ú§ä§î §á§â§Ö§â§í§Ó§Ñ§ß§Ú§Ö
    NVIC_EnableIRQ(SysTicK_IRQn);
    INT_enable();*/
  //*          
  

}

bool ClassSiren::isReedActive()
{
    uint8_t pin = PIN_read(PIN_ALARM_INPUT);
    PIN_write(PIN_ALARM_PSL, pin); // <-- send current status of the reed-contact to the ESP (switch_status[13])

    //check, if allow to use reed and device is active
    uint8_t pin_allow = PIN_read(PIN_ALARM_BREAK_A);
    bool result = (pin_allow == ALLOW_ALARM_ON);    //<-- if ESP allow to witch for  the reed, then do it

    if ( result )
    {
        result = (pin == ALARM_ON);  
    }

    return result;
}

bool ClassSiren::isESPBreaked()
{
    bool result = PIN_read(PIN_ESPALARM) == BREAK_ACTIVE;
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
    alarm_timeout = MIL_read();
    
    //alarm_timeout += (current_systick - last_sysTick);
    //last_sysTick = current_systick;

    if ( alarm_timeout > ALARM_BREAK_BY_TIME)
        alarm_timeout = ALARM_BREAK_BY_TIME;

    if ( a_state )
    {
        

        if  (
          ( alarm_timeout >= ALARM_BREAK_BY_TIME)
          //(alarm_active_counter >= ALARM_BREAK_BY_COUNT)
        
        )
        {
            //--DOES NOT RESET TRIGGER:triggerReedAlarm = false;
            setEspAlarmActive(false);
            espAlarmActive = true;  // <-- !!! This is very importent! without it will be reset espAlarmActive form esp 
            alarm_timeout = ALARM_BREAK_BY_TIME +1;
            PIN_write(PIN_ALARM_PS,  false );  // <-- switch off the syren only, but camera and ESP must have notification
            PIN_write(PIN_ALARM_PS,  false );  // <-- switch off the syren only, but camera and ESP must have notification
            PIN_write(PIN_ALARM_PS2, false ); 
            PIN_write(PIN_ALARM_PS2, false );
            return;
        }
    }

    tick_duration = alarm_timeout % (ALARM_PERIOD_ON + ALARM_PERIOD_OFF);
    //alarmPhase = tick_duration <  ALARM_PERIOD_ON;
    setAlarmPhase( tick_duration <  ALARM_PERIOD_ON );

           
    PIN_write(PIN_ALARM_PS,  alarmPhase && a_state ? ALARM_PULSE_ON : ALARM_PULSE_OFF ); // <-- a sirent
    PIN_write(PIN_ALARM_PS2, /*alarmPhase &&*/ a_state ? ALARM_PULSE_ON : ALARM_PULSE_OFF ); // <-- a ESP notification
}