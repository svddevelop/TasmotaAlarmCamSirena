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
#include "system.h"                               // system functions
#include "gpio.h"                                 // GPIO functions
#include "millis.h"

#ifndef __code
#define __code const __attribute__((section(".rodata")))
#endif

#include "sirendefines.h"
#include "ClassSieren.h"



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


/*

Check in for test:
1. Verify that Toggle2 turns the siren on and off. The siren should 
   produce intermittent beeps, while the camera output remains 
   continuously active.

2. Set Toggle1 to On and open the reed sensor: the siren activates 
   in the same way as in [1]. Turn Toggle2 on and off ¡ª the siren 
   should turn off, and the camera output should also turn off.

3. Set Toggle1 to On, open the reed sensor, and wait 6 minutes. 
   The siren and the camera should turn off after 6 minutes of activity.

*/


static ClassSiren* Siren;

static uint64_t counterr1 = 0;

// ===================================================================================
// Main Function
// ===================================================================================
int main(void) {

  STK_init();
   MIL_init();
  HSI_enable();

/*
  PIN_input(PIN_ALARM_INPUT);
  PIN_output(PIN_ALARM_PSL); 
    // §¯§Ñ§ã§ä§â§à§Û§ä§Ö §Ü§Ñ§Ü§à§Û-§ß§Ú§Ò§å§Õ§î §á§Ú§ß §Ü§Ñ§Ü §Ó§í§ç§à§Õ §Õ§Ý§ñ §Ú§ß§Õ§Ú§Ü§Ñ§è§Ú§Ú (§ß§Ñ§á§â§Ú§Þ§Ö§â, §ã§Ó§Ö§ä§à§Õ§Ú§à§Õ)
    PIN_output(PA1);  // §Ú§Ý§Ú §Ý§ð§Ò§à§Û §ã§Ó§à§Ò§à§Õ§ß§í§Û §á§Ú§ß
    
    while(1) {
        uint8_t pin_state = PIN_read(PIN_ALARM_INPUT);
        
        PIN_write(PIN_ALARM_PSL, pin_state);

        counterr1 += MIL_read();
        
        // §¯§Ö§Ò§à§Ý§î§ê§Ñ§ñ §Ù§Ñ§Õ§Ö§â§Ø§Ü§Ñ
        //DLY_ms(100);
    }
*/


  Siren = new ClassSiren();


  // Loop
  while(1)
    {

        Siren->run();
        counterr1 += MIL_read();
        

    }//while(1)
}