# Debugger Tutorial: Analyzing a BASIC Program

This tutorial will walk you through using the command-line debugger to inspect the execution of a simple BASIC program. This is a powerful way to understand how the C64's KERNAL and BASIC ROMs work together to run your code.

## Step 1: Write a Simple BASIC Program

First, run the emulator. At the `READY.` prompt, type in the following two-line program and press `Enter` after each line.

```basic
10 FOR I=0 TO 255
20 POKE 1024+I, I
```

This program loops 256 times, writing the values 0 through 255 into the screen's memory, which starts at address 1024 (`$0400`). This will create a visible pattern on the screen.

After typing the program, you can type `LIST` to verify it's entered correctly.

!Typing the BASIC Program  <!-- Placeholder for an image showing the BASIC program typed in -->

## Step 2: Enter the Debugger and Set a Breakpoint

Now, we want to inspect the program as it runs. We will set a breakpoint at the beginning of the BASIC interpreter's main loop, which is responsible for fetching and executing each line of our program.

1.  Press the **`F3`** key. This will pause the emulator and drop you into the command-line debugger in your terminal. You will see the current CPU state and a `>` prompt.

2.  The main loop of the BASIC interpreter starts at address `$A480`. Let's set a breakpoint there. Type the following command and press `Enter`:

    ```
    b A480
    ```

    The debugger will confirm with `Breakpoint set at $A480`.

3.  Now, type `c` (for "continue") and press `Enter` to leave the debugger and resume emulation.

## Step 3: Run the Program

You are now back at the C64's `READY.` prompt. Type `RUN` and press `Enter`.

The screen will go blank, and the emulator will immediately pause. If you look at your terminal, you will see that the debugger has been triggered because the CPU's Program Counter (`PC`) has hit our breakpoint at `$A480`.

```
--- DEBUGGER ---
A:00 X:00 Y:01 PC:A480 SP:F9  Flags: N-B-IZC
--- Disassembly from $A480 ---
$A480: JSR $A52C
$A483: JSR $A660
$A486: JMP $A7AE
...
>
```

The BASIC ROM is now about to execute the first line of our program.

## Step 4: Inspecting Memory and Stepping

Let's see the program in action.

1.  **View Screen Memory**: Before we execute anything, let's look at the screen memory. Type `m 0400` and press `Enter`. You will see a block of memory, which is likely filled with spaces (`$20`).

    ```
    > m 0400
    --- Memory View from $0400 ---
    $0400: 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 | ................
    ...
    ```

2.  **Continue Execution**: Our breakpoint is at the start of the main loop. This loop runs once for each statement in our program. Let's type `c` and press `Enter` to let the interpreter execute one full statement (the `FOR` statement). The program will run for a moment and then hit the same breakpoint at `$A480` again.

3.  **Step Through the `POKE`**: Now the interpreter is about to execute our `POKE` statement. Type `c` again to let it run. It will hit the breakpoint at `$A480` a third time.

4.  **View Memory Again**: Now, let's look at the screen memory again. Type `m 0400` and press `Enter`.

    ```
    > m 0400
    --- Memory View from $0400 ---
    $0400: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F | ................
    $0410: 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F | ................
    ...
    ```

    Success! You can see that the `FOR...POKE` loop has run and filled the screen memory with the values 0 through 255, which correspond to various characters and symbols on the C64 screen.

## Step 5: Clean Up

To let the program finish without stopping, we can clear the breakpoint.

1.  Type `b clear all` and press `Enter`.
2.  Type `c` and press `Enter`.

The emulator will now run freely, and you will be returned to the `READY.` prompt. You can see the pattern created by the `POKE` commands on the C64 screen.

This tutorial provides a basic workflow for using the debugger to pause execution at a specific point and inspect the state of the machine. You can use this technique to explore any part of the C64's KERNAL or BASIC ROMs.