# HOUSE DESIGN AI

The language of designing one house on one surveyed piece of land, from survey
to an approved, walkable model. One canonical vocabulary for the Owner, for
documentation, and for every coding agent. Terms the Owner sees carry their
Persian equivalent in brackets; use exactly that Persian term in any Persian
output.

## People

**Owner** (مالک):
The person whose house is being designed and whose words the project records.
_Avoid_: Homeowner, client, user

**Approver** (تصویب‌کننده):
A named human who passes a gate. Usually the Owner, but any human the Owner
trusts may be one; an agent never is.
_Avoid_: Reviewer (for this role), signer

## Site

**Site** (سایت):
Everything the survey describes, including land, roads and features outside
the legal boundary.
_Avoid_: Land, property

**Parcel** (قطعه زمین):
The land inside the legal boundary.
_Avoid_: Plot, lot, land

**Buildable envelope** (محدوده مجاز ساخت):
The part of the parcel where building may go, always with a stated basis for
why.
_Avoid_: Building area, footprint (for this meaning)

**Owner statement** (اظهار مالک):
Something the Owner said about the site; evidence that confirms nothing by
itself.
_Avoid_: Claim, declaration

## Interview

**Answer** (پاسخ):
The Owner's words, recorded exactly as said.
_Avoid_: Response, input

**Interpretation** (برداشت):
What an agent understood from an answer; unconfirmed until the Owner confirms
it.
_Avoid_: Slot value, parse

**Contradiction** (تناقض):
Two wishes of the Owner that cannot both hold, settled only by the Owner's
choice.
_Avoid_: Conflict, clash

**Design brief** (خلاصه طراحی):
Everything learned about the household and its wishes, from which the space
program is built.
_Avoid_: Brief (alone), requirements

**Assumption** (فرض):
A value used without being known, and labelled as such.
_Avoid_: Default, guess

**Open question** (پرسش باز):
Something unknown that someone must answer; it may be a blocker.
_Avoid_: TODO, pending item

## Program

**Space requirement** (نیاز فضایی):
A kind of space the Owner needs, with a quantity and a size, such as two
bedrooms of about 14 m² each.
_Avoid_: Program item, room requirement, brief item

**Space program** (برنامه فضایی):
The full list of space requirements and the relationships between them; the
thing the program gate approves.
_Avoid_: Brief (a different, earlier record), room list, schedule

**Space relationship** (رابطه فضایی):
How two spaces should relate: connected, adjacent, near, visible or separated.
_Avoid_: Adjacency (as the general word), link

## Spaces and levels

**Space** (فضا):
A drawn area of the house with a function, on one level. One space
requirement is met by one or more spaces.
_Avoid_: Room (except when talking with the Owner)

**Zone** (حوزه):
A named group of spaces that share a privacy class, such as the night zone.
_Avoid_: Area, wing; never for a part of an open-plan room

**Floor** (کف):
The surface inside a space that people walk on and put furniture on.
_Avoid_: Floor for a storey ("second floor")

**Level** (تراز):
The height of a floor, shared by every space at that height, such as the entry
level or the lower level at −2.80 m.
_Avoid_: Floor, elevation (for this meaning)

**Storey** (طبقه):
The whole layer of the building from one level up to the next one above it.
_Avoid_: Floor, story

**Split level** (نیم‌طبقه):
A level offset from another by less than a storey and joined to it by a short
flight of stairs.
_Avoid_: Mezzanine, half floor

## Plans

**Concept proposal** (پیشنهاد اولیه):
A structured idea of how to organise the house (levels, zones, links), given
to the solver before any plan exists.
_Avoid_: Concept, sketch

**Plan option** (گزینه طرح):
One named design idea with its own approach and history, such as Option B. A
request for something different makes a new option.
_Avoid_: Concept, design, scheme, alternative

**Plan version** (نسخه طرح):
One numbered, unchangeable save of a plan option, such as Option B v3. A
request to change an option makes its next version; a gate approves exactly one
version.
_Avoid_: Plan (alone), revision, draft

**Enclosure**:
The walls, openings, slabs and ceilings derived around the spaces of a plan
version, whichever strategy placed the spaces.
_Avoid_: Envelope (a buildable envelope is something else), shell

## Evidence

**Confirmed** (تأییدشده):
One value accepted by a human, such as a unit or a size the Owner agreed to.
It can still be rejected or revised later.
_Avoid_: Approved, verified (for this meaning)

**Approved** (تصویب‌شده):
A whole pinned version passed at a gate by an Approver. Only reopening the gate
undoes it.
_Avoid_: Confirmed, accepted, signed off

**Verified fact** (واقعیت محرز):
A claim whose status is established fact. "Verified" is never used alone.
_Avoid_: Verified, true, certain

## Evaluation

**Constraint** (قید):
A rule a plan must meet (hard) or should meet (soft).
_Avoid_: Rule (alone), requirement

**Evaluation** (ارزیابی):
All the findings and measurements about one plan version, each saying how it
was obtained.
_Avoid_: Score, assessment, review

**Finding** (یافته):
Anything a check reports about a site, program or plan.
_Avoid_: Problem, error (as the general word)

**Violation** (تخطی):
A finding against a named constraint, with a strength: hard or soft.
_Avoid_: Failure, breach

**Blocker** (مانع):
A finding or open question that keeps a gate closed.
_Avoid_: Showstopper, blocking issue

**Issue**:
An unresolved problem attached to a site or a house model.
In the development process an `ISS-` item is a different thing: a tracker
issue.
_Avoid_: Bug, defect (for this meaning)

## Workflow

**Workflow state** (وضعیت پروژه):
Where a project currently is in its lifecycle, from new project to Unreal
review.
_Avoid_: Stage, phase, step

**Gate** (نقطه تصویب):
A point in the workflow that only an Approver can pass, approving one pinned
version: site, program, plan or model.
_Avoid_: Checkpoint, milestone

## Development process

**Stage**:
One unit of tracker work on its own branch, reviewed independently before it
is closed. Never a workflow state.
_Avoid_: Sprint, phase

**Milestone**:
A historical group of stages (A to D) kept as record.
_Avoid_: Release, version
