/**
 * @title How much time do things take up?
 * @description Proportion experiment measuring temporal overlap.
 * @version 0.3.3
 *
 * @assets assets/
 */

import "../styles/main.scss";
import "../styles/proportion.scss";

import FullscreenPlugin from "@jspsych/plugin-fullscreen";
import jsPsychSurveyText from '@jspsych/plugin-survey-text';
import jsPsychSurveyLikert from '@jspsych/plugin-survey-likert';
import { initJsPsych } from "jspsych";

// Turn debug mode on when testing locally.
const debugMode = true;

// Define the conditions.
const conditions = [
  "contentful",
  "bleached",
  "templatic"
];

// Load the items.
const items = require('./proportion-items.json');

// Compute the number of lists for each condition.
const numLists = {};

for (var i = 0; i < conditions.length; i++) {
  numLists[conditions[i]] = items[conditions[i]].length;
} 

// Define the number of participants per list for each condition.
const numParticipantsPerList = {
  "contentful": 15, // target is 10 
  "bleached": 25, // target is 20
  "templatic": 45 // target is 40
};

// Define the instructions to be used for each condition.
const instructions = {
  "contentful": `
  <p class="instructions">
    In this study, we are interested in how long things tend to take. To investigate this question, 
    we will give you a sentence describing something that happened, along with some amount of time, and 
    we will ask you what proportion of that time (if any) that thing took up.
  </p>
  
  <p class="instructions">
    For example, you might receive the following sentence and question:
  </p>
  
  <div class="jspsych-content-wrapper">
    <div id="jspsych-content" class="jspsych-content">
      <style id="jspsych-survey-likert-css">.jspsych-survey-likert-statement { display:block; font-size: 16px; padding-top: 40px; margin-bottom:10px; }.jspsych-survey-likert-opts { list-style:none; width:100%; margin:auto; padding:0 0 35px; display:block; font-size: 14px; line-height:1.1em; }.jspsych-survey-likert-opt-label { line-height: 1.1em; color: #444; }.jspsych-survey-likert-opts:before { content: ''; position:relative; top:11px; /*left:9.5%;*/ display:block; background-color:#efefef; height:4px; width:100%; }.jspsych-survey-likert-opts:last-of-type { border-bottom: 0; }.jspsych-survey-likert-opts li { display:inline-block; /*width:19%;*/ text-align:center; vertical-align: top; }.jspsych-survey-likert-opts li input[type=radio] { display:block; position:relative; top:0; left:50%; margin-left:-6px; }</style>
      <form id="jspsych-survey-likert-form" autocomplete="off">
        <label class="jspsych-survey-likert-statement">
          <span class="sentence"><span class="clause">The child ate the sandwich</span> in <span class="time">5 minutes</span>.</span>
          <br>
            <span class="question">For what proportion of <span class="time">those 5 minutes</span> (if any) <span class="clause">was the child likely eating the sandwich</span>?</span>
          </label>
          <ul class="jspsych-survey-likert-opts" data-radio-group="Q0">
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="0">None of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="1">Less than half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="2">About half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="3" checked="checked">More than half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="4">The entirety of those 5 minutes
              </label>
            </li>
          </ul>
      </form>
    </div>
  </div>

  <p class="instructions">
    A natural response might be <i>more than half of those 5 minutes</i>. Alternatively, you might 
    think that eating a sandwich would take up all of those five minutes, in which case you would respond
    <i>the entirety of those 5 minutes</i>, or you might think that eating a sandwich would take up
    only <i>about half of those 5 minutes</i>. Multiple answers may make sense, and you should click the
    response you think is most likely.
  </p>
  
  <p class="instructions">
    In certain cases, the thing that happened may not take any of the time mentioned in the sentence.
    For example, you might receive the following sentence and question:
  </p>

  <div class="jspsych-content-wrapper">
    <div id="jspsych-content" class="jspsych-content">
      <style id="jspsych-survey-likert-css">.jspsych-survey-likert-statement { display:block; font-size: 16px; padding-top: 40px; margin-bottom:10px; }.jspsych-survey-likert-opts { list-style:none; width:100%; margin:auto; padding:0 0 35px; display:block; font-size: 14px; line-height:1.1em; }.jspsych-survey-likert-opt-label { line-height: 1.1em; color: #444; }.jspsych-survey-likert-opts:before { content: ''; position:relative; top:11px; /*left:9.5%;*/ display:block; background-color:#efefef; height:4px; width:100%; }.jspsych-survey-likert-opts:last-of-type { border-bottom: 0; }.jspsych-survey-likert-opts li { display:inline-block; /*width:19%;*/ text-align:center; vertical-align: top; }.jspsych-survey-likert-opts li input[type=radio] { display:block; position:relative; top:0; left:50%; margin-left:-6px; }</style>
      <form id="jspsych-survey-likert-form" autocomplete="off">
        <label class="jspsych-survey-likert-statement">
          <span class="sentence"><span class="clause">The plumber arrived</span> in <span class="time">20 minutes</span>.</span>
          <br>
            <span class="question">For what proportion of <span class="time">those 20 minutes</span> (if any) <span class="clause">was the plumber likely arriving</span>?</span>
          </label>
          <ul class="jspsych-survey-likert-opts" data-radio-group="Q0">
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="0" checked="checked">None of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="1">Less than half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="2">About half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="3">More than half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="4">The entirety of those 20 minutes
              </label>
            </li>
          </ul>
      </form>
    </div>
  </div>

  <p class="instructions">
    In this case, we know that the arrival didn't take any of the 20 minutes mentioned because
    it happened only after those 20 minutes had elapsed, so you would answer <i>none of those 20 minutes</i>.
    Answering <i>less than half of those 20 minutes</i> would also be correct, but if you can answer
    <i>none of those 20 minutes</i>, as you can here, you should.
  </p>

  <p class="instructions">
      This research is being carried out by Dr. Aaron White at the University of Rochester. You can read more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>. Upon clicking continue, you will enter fullscreen mode.
  </p>
  `,
  "bleached": `
  <p class="instructions">
    In this study, we are interested in how long things tend to take. To investigate this question, 
    we will give you a sentence describing something that happened, along with some amount of time, and 
    we will ask you what proportion of that time (if any) that thing took up.
  </p>
  
  <p class="instructions">
    For example, you might receive the following sentence and question:
  </p>
  
  <div class="jspsych-content-wrapper">
    <div id="jspsych-content" class="jspsych-content">
      <style id="jspsych-survey-likert-css">.jspsych-survey-likert-statement { display:block; font-size: 16px; padding-top: 40px; margin-bottom:10px; }.jspsych-survey-likert-opts { list-style:none; width:100%; margin:auto; padding:0 0 35px; display:block; font-size: 14px; line-height:1.1em; }.jspsych-survey-likert-opt-label { line-height: 1.1em; color: #444; }.jspsych-survey-likert-opts:before { content: ''; position:relative; top:11px; /*left:9.5%;*/ display:block; background-color:#efefef; height:4px; width:100%; }.jspsych-survey-likert-opts:last-of-type { border-bottom: 0; }.jspsych-survey-likert-opts li { display:inline-block; /*width:19%;*/ text-align:center; vertical-align: top; }.jspsych-survey-likert-opts li input[type=radio] { display:block; position:relative; top:0; left:50%; margin-left:-6px; }</style>
      <form id="jspsych-survey-likert-form" autocomplete="off">
        <label class="jspsych-survey-likert-statement">
          <span class="sentence"><span class="clause">The person ate the thing</span> in <span class="time">5 minutes</span>.</span>
          <br>
            <span class="question">For what proportion of <span class="time">those 5 minutes</span> (if any) <span class="clause">was the person likely eating the thing</span>?</span>
          </label>
          <ul class="jspsych-survey-likert-opts" data-radio-group="Q0">
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="0">None of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="1">Less than half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="2">About half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="3" checked="checked">More than half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="4">The entirety of those 5 minutes
              </label>
            </li>
          </ul>
      </form>
    </div>
  </div>

  <p class="instructions">
    A natural response might be <i>more than half of those 5 minutes</i>. Alternatively, you might 
    think that eating something would take up all of those five minutes, in which case you would respond
    <i>the entirety of those 5 minutes</i>, or you might think that eating something would take up
    only <i>about half of those 5 minutes</i>. Multiple answers may make sense, and you should click the
    response you think is most likely.
  </p>
  
  <p class="instructions">
    In certain cases, the thing that happened may not take any of the time mentioned in the sentence.
    For example, you might receive the following sentence and question:
  </p>

  <div class="jspsych-content-wrapper">
    <div id="jspsych-content" class="jspsych-content">
      <style id="jspsych-survey-likert-css">.jspsych-survey-likert-statement { display:block; font-size: 16px; padding-top: 40px; margin-bottom:10px; }.jspsych-survey-likert-opts { list-style:none; width:100%; margin:auto; padding:0 0 35px; display:block; font-size: 14px; line-height:1.1em; }.jspsych-survey-likert-opt-label { line-height: 1.1em; color: #444; }.jspsych-survey-likert-opts:before { content: ''; position:relative; top:11px; /*left:9.5%;*/ display:block; background-color:#efefef; height:4px; width:100%; }.jspsych-survey-likert-opts:last-of-type { border-bottom: 0; }.jspsych-survey-likert-opts li { display:inline-block; /*width:19%;*/ text-align:center; vertical-align: top; }.jspsych-survey-likert-opts li input[type=radio] { display:block; position:relative; top:0; left:50%; margin-left:-6px; }</style>
      <form id="jspsych-survey-likert-form" autocomplete="off">
        <label class="jspsych-survey-likert-statement">
          <span class="sentence"><span class="clause">The person arrived</span> in <span class="time">20 minutes</span>.</span>
          <br>
            <span class="question">For what proportion of <span class="time">those 20 minutes</span> (if any) <span class="clause">was the person likely arriving</span>?</span>
          </label>
          <ul class="jspsych-survey-likert-opts" data-radio-group="Q0">
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="0" checked="checked">None of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="1">Less than half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="2">About half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="3">More than half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="4">The entirety of those 20 minutes
              </label>
            </li>
          </ul>
      </form>
    </div>
  </div>

  <p class="instructions">
    In this case, we know that the arrival didn't take any of the 20 minutes mentioned because
    it happened only after those 20 minutes had elapsed, so you would answer <i>none of those 20 minutes</i>.
    Answering <i>less than half of those 20 minutes</i> would also be correct, but if you can answer
    <i>none of those 20 minutes</i>, as you can here, you should.
  </p>

  <p class="instructions">
      This research is being carried out by Dr. Aaron White at the University of Rochester. You can read more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>. Upon clicking continue, you will enter fullscreen mode.
  </p>
  `,
  "templatic": `
  <p class="instructions">
    In this study, we are interested in how long things tend to take. To investigate this question, 
    we will give you a sentence describing something that happened, along with some amount of time, and 
    we will ask you what proportion of that time (if any) that thing took up.
  </p>
  
  <p class="instructions">
    For example, you might receive the following sentence and question:
  </p>
  
  <div class="jspsych-content-wrapper">
    <div id="jspsych-content" class="jspsych-content">
      <style id="jspsych-survey-likert-css">.jspsych-survey-likert-statement { display:block; font-size: 16px; padding-top: 40px; margin-bottom:10px; }.jspsych-survey-likert-opts { list-style:none; width:100%; margin:auto; padding:0 0 35px; display:block; font-size: 14px; line-height:1.1em; }.jspsych-survey-likert-opt-label { line-height: 1.1em; color: #444; }.jspsych-survey-likert-opts:before { content: ''; position:relative; top:11px; /*left:9.5%;*/ display:block; background-color:#efefef; height:4px; width:100%; }.jspsych-survey-likert-opts:last-of-type { border-bottom: 0; }.jspsych-survey-likert-opts li { display:inline-block; /*width:19%;*/ text-align:center; vertical-align: top; }.jspsych-survey-likert-opts li input[type=radio] { display:block; position:relative; top:0; left:50%; margin-left:-6px; }</style>
      <form id="jspsych-survey-likert-form" autocomplete="off">
        <label class="jspsych-survey-likert-statement">
          <span class="sentence"><span class="clause">X ate Y</span> in <span class="time">5 minutes</span>.</span>
          <br>
            <span class="question">For what proportion of <span class="time">those 5 minutes</span> (if any) <span class="clause">was X likely eating Y</span>?</span>
          </label>
          <ul class="jspsych-survey-likert-opts" data-radio-group="Q0">
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="0">None of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="1">Less than half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="2">About half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="3" checked="checked">More than half of those 5 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="4">The entirety of those 5 minutes
              </label>
            </li>
          </ul>
      </form>
    </div>
  </div>

  <p class="instructions">
    A natural response might be <i>more than half of those 5 minutes</i>. Alternatively, you might 
    think that eating something would take up all of those five minutes, in which case you would respond
    <i>the entirety of those 5 minutes</i>, or you might think that eating something would take up
    only <i>about half of those 5 minutes</i>. Multiple answers may make sense, and you should click the
    response you think is most likely.
  </p>
  
  <p class="instructions">
    In certain cases, the thing that happened may not take any of the time mentioned in the sentence.
    For example, you might receive the following sentence and question:
  </p>

  <div class="jspsych-content-wrapper">
    <div id="jspsych-content" class="jspsych-content">
      <style id="jspsych-survey-likert-css">.jspsych-survey-likert-statement { display:block; font-size: 16px; padding-top: 40px; margin-bottom:10px; }.jspsych-survey-likert-opts { list-style:none; width:100%; margin:auto; padding:0 0 35px; display:block; font-size: 14px; line-height:1.1em; }.jspsych-survey-likert-opt-label { line-height: 1.1em; color: #444; }.jspsych-survey-likert-opts:before { content: ''; position:relative; top:11px; /*left:9.5%;*/ display:block; background-color:#efefef; height:4px; width:100%; }.jspsych-survey-likert-opts:last-of-type { border-bottom: 0; }.jspsych-survey-likert-opts li { display:inline-block; /*width:19%;*/ text-align:center; vertical-align: top; }.jspsych-survey-likert-opts li input[type=radio] { display:block; position:relative; top:0; left:50%; margin-left:-6px; }</style>
      <form id="jspsych-survey-likert-form" autocomplete="off">
        <label class="jspsych-survey-likert-statement">
          <span class="sentence"><span class="clause">X arrived</span> in <span class="time">20 minutes</span>.</span>
          <br>
            <span class="question">For what proportion of <span class="time">those 20 minutes</span> (if any) <span class="clause">was X likely arriving</span>?</span>
          </label>
          <ul class="jspsych-survey-likert-opts" data-radio-group="Q0">
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="0" checked="checked">None of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="1">Less than half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="2">About half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="3">More than half of those 20 minutes
              </label>
            </li>
            <li style="width:18%">
              <label class="jspsych-survey-likert-opt-label">
                <input type="radio" name="Q0" value="4">The entirety of those 20 minutes
              </label>
            </li>
          </ul>
      </form>
    </div>
  </div>

  <p class="instructions">
    In this case, we know that the arrival didn't take any of the 20 minutes mentioned because
    it happened only after those 20 minutes had elapsed, so you would answer <i>none of those 20 minutes</i>.
    Answering <i>less than half of those 20 minutes</i> would also be correct, but if you can answer
    <i>none of those 20 minutes</i>, as you can here, you should.
  </p>

  <p class="instructions">
      This research is being carried out by Dr. Aaron White at the University of Rochester. You can read more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>. Upon clicking continue, you will enter fullscreen mode.
  </p>
  `
};

// Initialize the JATOS assignment queue.
function initBatchConditions() {
  // Populate the queue only once.
  if (!jatos.batchSession.defined("/lists_to_run")) {    
    var lists_to_run = [];

    for (var i = 0; i < conditions.length; i++){
      for (var j = 0; j < numLists[conditions[i]]; j++) {
        for (var k = 0; k < numParticipantsPerList[conditions[i]]; k++) {
          lists_to_run.push(
            {
              "condition": conditions[i],
              "list_num": j
            }
          );
        }
      }
    }

    // Store the available assignments.
    jatos.batchSession.set("lists_to_run", lists_to_run)
      .fail(initBatchConditions); // Retry a failed write.
  }

  return true;
}

// Select the next assignment.
var getNextList;

if (debugMode) {
  // Use a fixed assignment in debug mode.
  getNextList = function() {
    return {
      "condition": "contentful",
      "list_num": 0
    }
  }
} else {
  // Draw an assignment from the JATOS queue.
  getNextList = function() {
    // Read the remaining assignments.
    var lists_to_run = jatos.batchSession.get("lists_to_run");
    
    // Stop when the queue is empty.
    if (lists_to_run.length == 0) {
      alert("Error: max number of workers reached.");
      throw "Max number of workers reached.";
    }
    
    // Choose a remaining assignment.
    var randomIndex = Math.floor(Math.random() * lists_to_run.length);
    var randomList = lists_to_run[randomIndex];
    
    // Remove the chosen assignment from the queue.
    lists_to_run.splice(randomIndex, 1);
    
    // Persist the remaining assignments.
    jatos.batchSession.set("lists_to_run", lists_to_run).fail(
      function () {
        randomList = getNextList(); // Retry a failed write.
      }
    );
    
    return randomList;
  }
}

/**
 * jsPsych Builder calls this function to run the experiment.
 *
 * @type {import("jspsych-builder").RunFunction}
 */
export async function run({ assetPaths, input = {}, environment, title, version }) {
  // Initialize jspsych.
  const jsPsych = initJsPsych({
    show_progress_bar: true
  });

  if (!debugMode) {
    // Initialize the batch session if necessary.
    var initComplete = await initBatchConditions();

    jsPsych.data.addProperties(
      jatos.urlQueryParameters
    );
  }

  // Get the condition and list number.
  var currList = getNextList();

  // Create the timeline.
  const timeline = [];

  // Add the instructions page to the timeline.
  timeline.push({
    type: FullscreenPlugin,
    message: instructions[currList.condition],
    fullscreen_mode: true,
  });

  var items_shuffled = jsPsych.randomization.shuffle(
    items[currList.condition][currList.list_num]
  );

  // Add the trials to the timeline.
  for (let i = 0; i < items_shuffled.length; i++) {
    var trial = {
      type: jsPsychSurveyLikert,
      questions: [{
          prompt: items_shuffled[i].prompt , 
          name: items_shuffled[i].item_id, 
          labels: items_shuffled[i].options,
          required: true
      }]
    };
    timeline.push(trial);
  }

  // Add the comments box to the timeline.
  timeline.push({
    type: jsPsychSurveyText,
    questions: [
      {prompt: '<p>Please provide any feedback on the experiment.</p>', rows: 5}
    ]
  });

  await jsPsych.run(timeline);

  // Return the instance so jsPsych Builder can access the results.
  return jsPsych;
}
