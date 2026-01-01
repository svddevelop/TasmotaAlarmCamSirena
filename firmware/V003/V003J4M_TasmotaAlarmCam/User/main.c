//  This µC have 3 inputs signals:
//    PC1 - Alarm Input
//    PC2 - Alarm break (from µC)
//    PC3 - Alarm break (external button)
//
// ... and one output: 
//    PA1 - Alaram output (Piezo-buzzer Sirena)
//
// The external µC set the alarm-signal on "Alarm Input".
// The the alarm doesn't breaked, switched between 2 tones(phases).
// The alarm could be breaked from external µC ("Alarm break (from µC)" must be BREAK_ACTIVE)
//   or from the externam button "Alarm break (external button)" (it must be reise from BREAK_INACTIVE to BREAK_ACTIVE)

//
//  251208-1955 it works
// 

//  251225 - it was changed for tasmota camera1
//

// !!! whan need to append:
//   1) PIN_ALARM_BREAK_B need to change as output for tasmota on pin io14/io3 (type "switch")
//        it could be see the status 


// KiCAD project Z:\WI\pcb\ESP8266\Esp8266-DomoticzAlarm-2\Esp8266-DomoticzAlarm-2A.kicad_pro\Esp8266-DomoticzAlarm-2B

// ===================================================================================
// Libraries, Definitions and Macros
// ===================================================================================
#include <system.h>                               // system functions
#include <gpio.h>                                 // GPIO functions

#include "SYS/millis.h"
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
#define ALARMFROMESP

#define PIN_ALARM_PS        PA2     // (O)Alarm signal to the Piezo-Buzzer
#define PIN_ALARM_PS2       PD6     // (O)Alarm signal to the Piezo-Buzzer
#define PIN_ALARM_INPUT     PC1     // (I) Alarm input (reed)                     
#define PIN_ALARM_BREAK_A   PC2     // (I) the reaction                          
#define PIN_ALARM_PSL       PC4     // (O) Alarm for ESP

#define BREAK_ACTIVE        (1)
#define BREAK_INACTIVE      (0)

#define ALARM_PULSE_ON      (1)     // the Piezo-buzzer activated
#define ALARM_PULSE_OFF     (0)     // the Piezo-buzzer deactivated

#define ALARM_ON            (1)
#define ALARM_OFF           (0)

#define ALARM_PERIOD_ON     (1000)  // Period in ms, when the Piezo-buzzer is active
#define ALARM_PERIOD_OFF    (500)   // Period in ms, when the Piezo-buzzer is inactive




static struct{

  uint8_t breaked : 1;          //The breaked == BREAK_ACTIVE means that does not need  to do something for alarm
  uint8_t pulse_on: 1;          //When is alarm active, can be swithc between two phases : ALARM_PERIOD_ON and ALARM_PERIOD_OFF
  uint8_t last_break_a: 1;      //It shows that the break active from external µC and does not need to switch alarm
  uint8_t last_break_b: 1;
  uint8_t last_alarm: 1;

} g_status;

#define ALARM_PS(x)         PIN_write(PIN_ALARM_PS, x);PIN_write(PIN_ALARM_PS2, x)


// ===================================================================================
// Main Function
// ===================================================================================
int main(void) {

  STK_init();
  HSI_enable();


  // Setup
  PIN_output(PIN_ALARM_PS);                         // Alarm signal to the Piezo-Buzzer
  PIN_output(PIN_ALARM_PS2);                        // Alarm signal to the Piezo-Buzzer
  PIN_output(PIN_ALARM_PSL);                        // Alarm signal to the ESP
  PIN_write(PIN_ALARM_PS, ALARM_PERIOD_OFF);
  PIN_write(PIN_ALARM_PS2, ALARM_PERIOD_OFF);
  PIN_write(PIN_ALARM_PSL, ALARM_PERIOD_OFF);

  PIN_input_PU(PIN_ALARM_INPUT);                    // Alarm activation on reise from ALARM_OFF to ALARM_ON
  PIN_input(PIN_ALARM_BREAK_A);                  // Stop alarm. It going from µC
  //PIN_input(PIN_ALARM_BREAK_B);                  // With pull-up.  Stop alarm from the external button

  #ifdef ALARMFROMESP
  PIN_input_PU(PIN_ESPALARM);
  #endif


  
  //ALARM_PS(ALARM_PULSE_OFF);   
  PIN_write(PIN_ALARM_PS, ALARM_PULSE_OFF);
  PIN_write(PIN_ALARM_PS2, ALARM_PULSE_OFF);             

  g_status.breaked    =   BREAK_INACTIVE;
  g_status.pulse_on   =   ALARM_PULSE_ON;
  g_status.last_alarm =   ALARM_OFF;

  // Loop
  while(1) {

    uint8_t pin;



    //
    pin = PIN_read(PIN_ALARM_INPUT);
    PIN_write(PIN_ALARM_PSL, pin); 
    if ((pin == ALARM_ON) & (g_status.last_alarm == ALARM_OFF))
        g_status.last_alarm = ALARM_ON;

    //if (pin == ALARM_OFF)
    //    g_status.last_alarm = ALARM_OFF;

    //*/    

    //
    pin = PIN_read(PIN_ALARM_BREAK_A);

    if (( pin == BREAK_ACTIVE) )//& ( g_status.last_break_a == BREAK_INACTIVE))
    {

      g_status.breaked = BREAK_ACTIVE; 
      g_status.last_break_b = BREAK_INACTIVE;
    }
    else 
      g_status.breaked = BREAK_INACTIVE;

    g_status.last_break_a = pin;
    //*/


    // check for the break from the stop-alarm button
    pin = BREAK_INACTIVE;
    g_status.last_break_b = pin;
    //*
    #ifdef ALARMFROMESP
    pin = PIN_read(PIN_ESPALARM);
    if (( pin == ALARM_ON))// & ( g_status.last_break_b == BREAK_INACTIVE))  
    {
      g_status.breaked    = BREAK_INACTIVE; 
      g_status.last_alarm = ALARM_ON;
    }
    //g_status.last_break_b = pin;
    #endif
    //*/

    // switch alarm to OFF if any break is active
    if (g_status.breaked == BREAK_ACTIVE){

        //ALARM_PS(ALARM_PULSE_OFF);
        PIN_write(PIN_ALARM_PS, ALARM_PULSE_OFF);
        PIN_write(PIN_ALARM_PS2, ALARM_PULSE_OFF);             
        //PIN_write(PIN_ALARM_PSL, ALARM_PULSE_OFF);             
        g_status.last_alarm = ALARM_OFF;
    }
    //*/

    

    //
    //pin = ALARM_ON;
    //g_status.last_alarm = ALARM_OFF;

    if (g_status.last_alarm == ALARM_ON) {  

                   
      if (g_status.breaked == BREAK_INACTIVE){

        if (g_status.pulse_on == ALARM_PULSE_ON){

          //ALARM_PS(ALARM_PULSE_ON);
          PIN_write(PIN_ALARM_PS, ALARM_PULSE_ON);
          PIN_write(PIN_ALARM_PS2, ALARM_PULSE_ON);             
          g_status.pulse_on = ALARM_PULSE_OFF;
          DLY_ms(ALARM_PERIOD_ON);

        }
        else { //if (g_status.pulse_on == ALARM_PULSE_ON)

          //ALARM_PS(ALARM_PULSE_OFF);
          PIN_write(PIN_ALARM_PS, ALARM_PULSE_OFF);
          PIN_write(PIN_ALARM_PS2, ALARM_PULSE_OFF);             
          g_status.pulse_on = ALARM_PULSE_ON;
          DLY_ms(ALARM_PERIOD_OFF);

        }//if (g_status.pulse_on == ALARM_PULSE_ON)
        

      }//if (g_status.breaked == BREAK_ACTIVE)

    }//if ( pin == 1)
    //g_status.last_alarm = pin;
    //*

    //DLY_ms(400);                                  // wait a bit

  }//while(1)
}
