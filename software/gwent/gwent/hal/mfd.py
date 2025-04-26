import time
import logging
from typing import Any, Callable

import gwent.game
import gwent.hal
import gwent.hal.mfdi
import gwent.hal.rotary
import gwent.hal.console
import gwent.hal.oled_ssd1306
import gwent.messaging.base

import gwent.messaging.mfd
import gwent.messaging.choice


def instance():
    logger = logging.getLogger('gwent.hal.mfd')
    logger.info("Creating MFD instance")
    
    if gwent.hal.real_mode():
        logger.info("Running in real hardware mode")
        try:
            # Use device=1, port=0 as confirmed by the oled_test
            logger.info("Initializing SSD1306Presenter with device=1, port=0")
            presenter = gwent.hal.oled_ssd1306.SSD1306Presenter(device=1, port=0)
            logger.info("SSD1306Presenter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SSD1306Presenter: {e}", exc_info=True)
            raise
            
        try:
            logger.info("Initializing RotaryChooser")
            chooser = gwent.hal.rotary.RotaryChooser()
            logger.info("RotaryChooser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RotaryChooser: {e}", exc_info=True)
            raise
    else:
        logger.info("Running in simulation mode")
        try:
            logger.info("Initializing ConsolePresenter")
            presenter = gwent.hal.console.ConsolePresenter()
            logger.info("ConsolePresenter initialized successfully")
            
            logger.info("Initializing ConsoleChooser")
            chooser = gwent.hal.console.ConsoleChooser()
            logger.info("ConsoleChooser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize console components: {e}", exc_info=True)
            raise

    logger.info("Creating _MFD instance with presenter and chooser")
    
    mfd = _MFD(presenter, chooser)

    error_msg = gwent.messaging.mfd.Message.with_error("Test Message")
    mfd.present_error(error_msg, lambda delta, choice: None)

    return mfd


class _MFD(gwent.game.BaseComponent):

    def __init__(self, choice_presenter: gwent.hal.mfdi.Presenter, chooser: gwent.hal.mfdi.Chooser):
        super().__init__()
        self._log.info("Initializing _MFD component")
        
        if choice_presenter is None:
            self._log.error("choice_presenter is None")
            raise ValueError("choice_presenter cannot be None")
            
        if chooser is None:
            self._log.error("chooser is None")
            raise ValueError("chooser cannot be None")
            
        self._log.info(f"Using presenter: {choice_presenter.__class__.__name__}")
        self._presenter = choice_presenter
        
        self._log.info(f"Using chooser: {chooser.__class__.__name__}")
        self._chooser = chooser
        
        self._log.info("_MFD component initialized successfully")

    def present_error(
            self, mfd: gwent.messaging.mfd.Message,
            select: Callable[[int, gwent.messaging.choice.Message], Any],
            delay: int = gwent.game.DEFAULT_ERROR_TIME):
        self._log.info({
            'action': 'present_error',
            'error': mfd.error,
            'delay': delay
        })

        try:
            self._log.debug("Setting error message on presenter")
            self._presenter.error = mfd.error
            
            self._log.debug("Displaying error on presenter")
            self._presenter.display_error()
            
            self._log.debug("Redrawing presenter")
            self._presenter.redraw()
            
            if self._presenter.prompt:
                self._log.info(f"Prompt exists, sleeping for {delay}s before showing prompt")
                time.sleep(delay)
                self._log.debug("Displaying prompt")
                self._presenter.display_prompt()
                self._log.debug("Redrawing presenter")
                self._presenter.redraw()
            else:
                self._log.debug("No prompt to display after error")

            def _select(delta: int, choice: gwent.messaging.choice.Message):
                self._log.debug({
                    'action': '_select in present_error',
                    'delta': delta,
                    'choice_id': choice.id,
                    'choice_text': choice.text
                })
                self._presenter.select(delta, choice)
                select(delta, choice)

            choices_count = len(self._presenter.all_choices)
            self._log.info(f"Number of choices available: {choices_count}")
            
            if choices_count > 0:
                self._log.info("Calling chooser.choose() with choices")
                selected_idx = self._presenter.selected_idx
                self._log.debug(f"Selected index: {selected_idx}")
                return self._chooser.choose(
                    self._presenter.all_choices,
                    selected_idx,
                    _select)
            else:
                self._log.info("No choices available, returning None")
                return None
                
        except Exception as e:
            self._log.error(f"Error in present_error: {e}", exc_info=True)
            raise

    def present_prompt(
            self, mfd: gwent.messaging.mfd.Message,
            select: Callable[[int, gwent.messaging.choice.Message], Any]):
        self._log.info({
            'action': 'present_prompt',
            'prompt': mfd.prompt,
            'clear_choices': mfd.clear_choices,
            'has_ok': mfd.has_ok,
            'has_cancel': mfd.has_cancel
        })
        
        try:
            self._log.debug("Setting prompt on presenter")
            self._presenter.prompt = mfd.prompt
            
            self._log.debug("Displaying prompt")
            self._presenter.display_prompt()

            if mfd.clear_choices:
                self._log.debug("Clearing choices")
                self._presenter.clear_choices()

            if mfd.has_ok:
                if mfd.ok:
                    self._log.debug("Creating OK button")
                    ok = gwent.messaging.choice.Message.new_ok()
                else:
                    self._log.debug("Setting OK button to None")
                    ok = None
                self._log.debug(f"Setting OK button: {ok.id if ok else None}")
                self._presenter.ok = ok

            if mfd.has_cancel:
                if mfd.cancel:
                    self._log.debug("Creating Cancel button")
                    cancel = gwent.messaging.choice.Message.new_cancel()
                else:
                    self._log.debug("Setting Cancel button to None")
                    cancel = None
                self._log.debug(f"Setting Cancel button: {cancel.id if cancel else None}")
                self._presenter.cancel = cancel

            all_choices = self._presenter.all_choices
            choices_count = len(all_choices)
            self._log.info(f"Number of choices available: {choices_count}")
            
            if self._presenter.selected is None and choices_count > 0:
                self._log.debug("No selection, selecting first choice")
                self._presenter.select(0, all_choices[0])
            else:
                self._log.debug(f"Selection exists or no choices, redrawing")
                self._presenter.redraw()

            def _select(delta: int, choice: gwent.messaging.choice.Message):
                self._log.debug({
                    'action': '_select in present_prompt',
                    'delta': delta,
                    'choice_id': choice.id,
                    'choice_text': choice.text
                })
                self._presenter.select(delta, choice)
                select(delta, choice)

            if choices_count > 0:
                self._log.info("Calling chooser.choose() with choices")
                selected_idx = self._presenter.selected_idx
                self._log.debug(f"Selected index: {selected_idx}")
                return self._chooser.choose(
                    all_choices, selected_idx, _select)
            else:
                self._log.info("No choices available, returning None")
                return None
                
        except Exception as e:
            self._log.error(f"Error in present_prompt: {e}", exc_info=True)
            raise

    def present_choices(
            self, mfd: gwent.messaging.mfd.Message,
            select: Callable[[int, gwent.messaging.choice.Message], Any]):
        self._log.info({
            'action': 'present_choices',
            'choices_count': len(mfd.choices) if mfd.choices else 0,
            'clear_prompt': mfd.clear_prompt
        })
        
        try:
            if mfd.clear_prompt:
                self._log.debug("Clearing prompt")
                self._presenter.clear_prompt()

            self._log.debug("Clearing choices")
            self._presenter.clear_choices()
            
            if mfd.choices:
                self._log.debug(f"Setting {len(mfd.choices)} choices")
                choices = []
                for i, c in enumerate(mfd.choices):
                    choice = gwent.messaging.choice.Message.from_dict(c)
                    self._log.debug(f"Choice {i}: id={choice.id}, text={choice.text}")
                    choices.append(choice)
                self._presenter.choices = choices
            else:
                self._log.warning("No choices provided in mfd.choices")

            all_choices = self._presenter.all_choices
            choices_count = len(all_choices)
            self._log.info(f"Total choices (including OK/Cancel): {choices_count}")
            
            if self._presenter.selected is None and choices_count > 0:
                self._log.debug("No selection, selecting first choice")
                self._presenter.select(0, all_choices[0])
            else:
                self._log.debug("Selection exists or no choices, redrawing")
                self._presenter.redraw()

            def _select(delta: int, choice: gwent.messaging.choice.Message):
                self._log.debug({
                    'action': '_select in present_choices',
                    'delta': delta,
                    'choice_id': choice.id,
                    'choice_text': choice.text
                })
                self._presenter.select(delta, choice)
                select(delta, choice)

            if choices_count > 0:
                self._log.info("Calling chooser.choose() with choices")
                selected_idx = self._presenter.selected_idx
                self._log.debug(f"Selected index: {selected_idx}")
                return self._chooser.choose(
                    all_choices, self._presenter.selected_idx, _select)
            else:
                self._log.info("No choices available, returning None")
                return None
                
        except Exception as e:
            self._log.error(f"Error in present_choices: {e}", exc_info=True)
            raise
