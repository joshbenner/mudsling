Feature: Roleplay

  Background: Couple people RPing together.
    Given Bob is connected
    And Alice is connected
    And A room called "RP Room" exists
    And Bob is in RP Room
    And Alice is in RP Room

  Scenario: Standard emote.
    When Bob enters "emote waves."
    Then Alice should see "Bob waves."

  Scenario: Emote shortcut.
    When Bob enters ":waves."
    Then Alice should see "Bob waves."

  Scenario: Standard say.
    When Bob enters "say Hi!"
    Then Alice should see 'Bob says, "Hi!"'

  Scenario: Say shortcut.
    When Bob enters '"Hi!'
    Then Alice should see 'Bob says, "Hi!"'