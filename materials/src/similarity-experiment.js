/**
 * @title How different are these two situations?
 * @description Pairwise event-description similarity experiment.
 * @version 0.4.0a
 *
 * @assets assets/
 */

import "../styles/main.scss";
import "../styles/similarity.scss";

import FullscreenPlugin from "@jspsych/plugin-fullscreen";
import jsPsychSurveyText from '@jspsych/plugin-survey-text';
import jsPsychHtmlSliderResponse from '@jspsych/plugin-html-slider-response';
import { initJsPsych } from "jspsych";

// Turn debug mode on when testing locally.
const debugMode = true;

// Load the items.
const items = require('./similarity-items.json');

// Compute the number of lists for each condition.
const numLists = items.length;

// Define the number of participants per list for each condition.
const numParticipantsPerList = 15; // target is 10

// Define the instructions to be used for each condition.
const instructions = `
  <p class="instructions">
    In this study, we are interested in how different situations are from each other. To investigate this question, 
    we will give you two sentences describing situations, and we will ask you to judge how 
    different those situations are using a slider.
  </p>
  
  <p class="instructions">
    For example, you might receive the following two sentences:
  </p>

  <div id="jspsych-html-slider-response-wrapper" style="margin: 0px 0px;"><div id="jspsych-html-slider-response-stimulus">
      <p>The athlete ran the marathon.</p>
      <p>The CEO ran the company.</p>
    </div><div class="jspsych-html-slider-response-container" style="position:relative; margin: 0 auto 3em auto; width:50%;"><input type="range" class="jspsych-slider" value="90" min="0" max="100" step="1" id="jspsych-html-slider-response-response"><div><div style="border: 1px solid transparent; display: inline-block; position: absolute; left:calc(0% - (100% / 2) - -7.5px); text-align: center; width: 100%;"><span style="text-align: center; font-size: 80%;"><span class="identical">completely <b>identical</b></span></span></div><div style="border: 1px solid transparent; display: inline-block; position: absolute; left:calc(100% - (100% / 2) - 7.5px); text-align: center; width: 100%;"><span style="text-align: center; font-size: 80%;"><span class="different">extremely <b>different</b></span></span></div></div></div></div>
  
  <p class="instructions">
    A natural response might be that the situations described by these two sentences are very different, 
    and so you would slide the slider pretty far to the right. 
  </p>
  
  <p class="instructions">
    You might also receive the following two sentences:
  </p>

  <div id="jspsych-html-slider-response-wrapper" style="margin: 0px 0px;"><div id="jspsych-html-slider-response-stimulus">
    <p>The teenager ran the 800m.</p>
    <p>The highschooler ran the race.</p>
  </div><div class="jspsych-html-slider-response-container" style="position:relative; margin: 0 auto 3em auto; width:50%;"><input type="range" class="jspsych-slider" value="5" min="0" max="100" step="1" id="jspsych-html-slider-response-response"><div><div style="border: 1px solid transparent; display: inline-block; position: absolute; left:calc(0% - (100% / 2) - -7.5px); text-align: center; width: 100%;"><span style="text-align: center; font-size: 80%;"><span class="identical">completely <b>identical</b></span></span></div><div style="border: 1px solid transparent; display: inline-block; position: absolute; left:calc(100% - (100% / 2) - 7.5px); text-align: center; width: 100%;"><span style="text-align: center; font-size: 80%;"><span class="different">extremely <b>different</b></span></span></div></div></div></div>
  
  <p class="instructions">
    In this case, you might judge these as nearly identical (if not completely identical), so you would 
    slide the slider pretty far to the left. 
  </p>

  <p class="instructions">
    The slider will always start at <span class="identical">completely <b>identical</b></span> on the left, 
    and you will need to move the slider in order to submit your response. If you judge the two situations
    to be completely identical, you can simply click on the slider and response submission will become available.
  </p>

  <p class="instructions">
    This research is being carried out by Dr. Aaron White at the University of Rochester. You can read 
    more about the study <a target=”_blank” href="http://factslab.io/information_sheet_021523.pdf">here</a>.
    Upon clicking continue, you will enter fullscreen mode.
  </p>
`;

let base_prompt = "How different are the situations described by the following two sentences?";

// Initialize the JATOS assignment queue.
function initBatchConditions() {
  // Populate the queue only once.
  if (!jatos.batchSession.defined("/lists_to_run")) {    
    var lists_to_run = [];

    for (var j = 0; j < numLists; j++) {
      for (var k = 0; k < numParticipantsPerList; k++) {
        lists_to_run.push({
            "list_num": j
        });
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
    message: instructions,
    fullscreen_mode: true,
  });

  let calibration_items = [
    {
      item_id: "calibration_somewhat_similar-1",
      sentence1: "The architect designed the building.",
      sentence2: "The strategist designed the message."
    },
    {
      item_id: "calibration_somewhat_different-1", 
      sentence1: "The college permitted the event.", 
      sentence2: "The weather permitted the picnic."
    },
    {
      item_id: "calibration_very_different-1",
      sentence1: "The player bounced the ball.",
      sentence2: "The bank bounced the check."
    },
    {
      item_id: "calibration_very_similar-1",
      sentence1: "The dog scratched the itch.", 
      sentence2: "The patient scratched the rash."
    },
    {
      item_id: "calibration_somewhat_different-2",
      sentence1: "The botanist recognized the mushroom.",
      sentence2: "The king recognized the bravery."
    },
    {
      item_id: "calibration_somewhat_similar-2",
      sentence1: "The company dismissed the worker.",
      sentence2: "The teacher dismissed the class."
    },
    {
      item_id: "calibration_very_similar-2",
      sentence1: "The mailman delivered the package.",
      sentence2: "The visitor delivered the gift."
    },
    {
      item_id: "calibration_very_different-2",
      sentence1: "The thief stole the painting.",
      sentence2: "The dancer stole the show."
    }
  ];

  // Add the calibration trials to the timeline.
  for (let i = 0; i < calibration_items.length; i++) {
    let sentences = [
      calibration_items[i].sentence1,
      calibration_items[i].sentence2
    ];
    let sentences_shuffled = jsPsych.randomization.shuffle(
      sentences
    );

    let prompt = `
      <div class="itemid">${calibration_items[i].item_id}</div>
      <p class="prompt">${base_prompt}</p>\
      <p>${sentences_shuffled[0]}</p>
      <p>${sentences_shuffled[1]}</p>
    `;

    var trial = {
      type: jsPsychHtmlSliderResponse,
      stimulus: prompt,
      require_movement: true,
      slider_start: 0,
      labels: ['<span class="identical">completely <b>identical</b></span>', '<span class="different">extremely <b>different</b></span>']
    };
    timeline.push(trial);
  }

  var items_shuffled = jsPsych.randomization.shuffle(
    items[currList.list_num]
  );

  // Add the test trials to the timeline.
  for (let i = 0; i < items_shuffled.length; i++) {
    let sentences = [
      items_shuffled[i].sentence1,
      items_shuffled[i].sentence2
    ];
    let sentences_shuffled = jsPsych.randomization.shuffle(
      sentences
    );
    let item_id = sentences.join("%") + "%_%" + sentences_shuffled.join("%");

    let prompt = `
      <div class="itemid">${item_id}</div>
      <p class="prompt">${base_prompt}</p>\
      <p>${sentences_shuffled[0]}</p>
      <p>${sentences_shuffled[1]}</p>
    `;

    var trial = {
      type: jsPsychHtmlSliderResponse,
      stimulus: prompt,
      require_movement: true,
      slider_start: 0,
      labels: ['<span class="identical">completely <b>identical</b></span>', '<span class="different">extremely <b>different</b></span>']
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
