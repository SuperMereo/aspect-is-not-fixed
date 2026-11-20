import { JsPsych, JsPsychPlugin, ParameterType, TrialType } from "jspsych";

const info = <const>{
  name: "cloze-dropdown",
  parameters: {
    text: {
      type: ParameterType.HTML_STRING,
      pretty_name: "Cloze text",
      default: undefined,
    },
    blanks: {
      type: ParameterType.COMPLEX,
      array: true,
      nested: {
        name: {
          type: ParameterType.STRING,
          description: 'Optional text to use as field name when logging responses.',
          default: null
        },
        choices: {
          type: ParameterType.FUNCTION,
          array: true,
          description: 'A function returning an array of possible choices conditioned on the current state.'
        },
        placeholder: {
          type: ParameterType.STRING,
          description: 'Optional text to use as a placeholder.',
          default: null
        }
      }
    }
  },
};

type Info = typeof info;

/**
 * **clozeDropdown**
 *
 * {description}
 *
 * @author Aaron Steven White
 * @see {@link url}
 */
class ClozeDropdownPlugin implements JsPsychPlugin<Info> {

  static info = info;

  constructor(private jsPsych: JsPsych) {}

  buildBlankId(i: number): string {
    return 'clozeDropdownBlank' + i;
  }

  getBlank(display_element: HTMLElement, i: number) {
    var blankId = this.buildBlankId(i)
    return display_element.querySelector('#'+blankId);
  }

  getState(display_element: HTMLElement, trial: TrialType<Info>) {
    var answers = {};
    var isComplete = true;

    for (var i = 0; i < trial.blanks.length; i++) {
      var blankName = trial.blanks[i].name;
      var blank = this.getBlank(display_element, i);
      answers[blankName] = blank.value.trim();

      if (blank.placeholder && answers[i] === blank.placeholder) {
        isComplete = false;
      } else if (answers[blankName] === "") {
        isComplete = false;
      }
    }

    return {
      "answers": answers,
      "isComplete": isComplete
    };
  }

  onSubmit(display_element: HTMLElement, trial: TrialType<Info>, response_times) {
    var state = this.getState(display_element, trial);

    if (!state.isComplete) {
      trial.mistake_fn();
    } else {
      // Save trial data.
      var trialData = {
        "response_times": response_times,
        "text": trial.text,
        "responses": state.answers,
      };

      // End the trial.
      this.jsPsych.finishTrial(trialData);
    }
  }

  buildSelectionDiv(trial: TrialType<Info>, subtexts: string[]) {
    var html = '<div class="clozeDropdown">';

    for (var i = 0; i < trial.blanks.length; i++) {
      html += subtexts[i];

      var blankId = this.buildBlankId(i);

      // Add the selection element.
      html += '<select id="' + blankId + '" name="' + blankId + '" required>'

      // Add the placeholder option.
      var blank = trial.blanks[i]
      var placeholderText = blank.placeholder || '';
      var placeholderHtml = '<option selected disabled value="">' + placeholderText + '</option>';

      html += placeholderHtml;

      var initAnswers = {};

      for (var j = 0; j < trial.blanks.length; j++) {
        var blankName = trial.blanks[j].name;
        initAnswers[blankName] = "";
      }

      // Add the response options.
      var choices = blank.choices(initAnswers);

      for (var k = 0; k < choices.length; k++) {
        html += '<option value="' + choices[k] + '">' + choices[k] + '</option>'
      }

      // Finish the selection element.
      html += '</select>';
    }

    if (i < subtexts.length) {
      html += subtexts[i];
    }
    
    html += "</div>";

    return html;
  }

  logTime(blank, name, response_times, start_time: number) {
    var end_time = (new Date()).getTime();

    response_times.push({
      "id": name || blank.id,
      "time": end_time - start_time,
      "value": blank.value
    });
  }

  updateChoices(display_element, trial) {
    var state = this.getState(display_element, trial);

    for (var i = 0; i < trial.blanks.length; i++) {
      var blankElement = this.getBlank(display_element, i);
      var choices = trial.blanks[i].choices(state.answers);

      for (var j = 0; j < blankElement.children.length; j++) {
        var option = blankElement.children[j]

        if (option.value != "") {
          option.text = choices[j-1];
        }
      }
    }
  }

  trial(display_element: HTMLElement, trial: TrialType<Info>) {
    var subtexts = trial.text.split("%_%");

    if (trial.blanks.length != subtexts.length - 1) {
      console.log("Number of blanks differ from number specified in text.");
    }

    display_element.innerHTML = this.buildSelectionDiv(trial, subtexts);
    display_element.innerHTML += '<br><button class="jspsych-html-button-response-button" type="button" id="finish_cloze_dropdown_button">Next</button>';

    var responseTimes = [];

    display_element.querySelector(
      "#finish_cloze_dropdown_button"
    ).addEventListener(
      "click", 
      () => this.onSubmit(display_element, trial, responseTimes)
    );

    var startTime = (new Date()).getTime();

    for (var i = 0; i < trial.blanks.length; i++) {
      let blank = this.getBlank(display_element, i);
      let name = trial.blanks[i].name;
      let logger = () => this.logTime(blank, name, responseTimes, startTime);

      blank.addEventListener(
        "change", 
        () => {
          logger();
          this.updateChoices(display_element, trial);
        }
      );
    }
  };
}

ClozeDropdownPlugin.info = info;

export default ClozeDropdownPlugin;
